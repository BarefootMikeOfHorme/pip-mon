# =============================================================
#  approve.ps1 -- show a decision set in a window and wait for OK.
#
#  WHY THIS EXISTS
#    Stage 2 costs ~2m15s of xEdit load before it can fail, and a compile
#    error in the script costs another full load to discover. Reviewing the
#    decisions in a terminal is fine until the terminal is a transcript nobody
#    re-reads. This puts them in one window with one button, and blocks until
#    the answer is given -- so "approved" is a fact with a timestamp rather
#    than an assumption inside a control-flow branch.
#
#  IT BLOCKS BY DESIGN. That is the one property that makes it worth having:
#  an approval that returns immediately is not an approval.
#
#    tools\approve.ps1 -Title "..." -Body "..."          # plain text body
#    tools\approve.ps1 -DecisionsFile path.json          # structured list
#
#  EXIT CODES
#    0  APPROVED
#    3  DECLINED  (closed the window)
#    2  BROKEN    (no GUI available, e.g. running over a plain SSH/pwsh session)
# =============================================================
[CmdletBinding()]
param(
    [string]$Title = 'PIP-MON - review and approve',
    [string]$Body = '',
    [string]$DecisionsFile = '',
    [int]$TimeoutSec = 0,
    [switch]$AutoApprove
)

$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
Add-Type -AssemblyName System.Drawing -ErrorAction SilentlyContinue

# A headless session cannot show a window. Say so and take the answer from the
# argument rather than silently blocking forever on a dialog nobody can see.
if ($AutoApprove) {
    $stampA = (Get-Date).ToString('o')
    $logDirA = Join-Path (Split-Path -Parent $PSScriptRoot) 'runs\watch'
    New-Item -ItemType Directory -Path $logDirA -Force | Out-Null
    [ordered]@{ approved = $true; stamp = $stampA; title = $Title; task = $Body } |
        ConvertTo-Json -Depth 4 | Add-Content -LiteralPath (Join-Path $logDirA 'approvals.jsonl') -Encoding utf8
    Write-Output ("APPROVED at " + $stampA + " (auto, no GUI)")
    exit 0
}

if (-not ('PipMon.ApproveForm' -as [type])) {
# -ReferencedAssemblies is required: loading the assembly into the AppDomain is
# not enough for the C# compiler, and without it Add-Type fails with
# "The type or namespace name 'Forms' does not exist in the namespace
# 'System.Windows'" -- which reads like a missing Windows feature and is not.
Add-Type -ReferencedAssemblies 'System.Windows.Forms.dll', 'System.Drawing.dll' @'
using System;
using System.Drawing;
using System.Windows.Forms;

namespace PipMon
{
    public class ApproveForm : Form
    {
        public bool Approved = false;
        public TextBox   BodyBox;
        public DateTime  Stamp = DateTime.MinValue;

        public ApproveForm(string title, string text)
        {
            this.Text = title;
            this.Width = 1000;
            this.Height = 720;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.BackColor = Color.FromArgb(30, 30, 30);
            this.ForeColor = Color.White;
            this.Font = new Font("Consolas", 10.5f);

            var lbl = new Label();
            lbl.Text = title;
            lbl.Font = new Font("Segoe UI", 13f, FontStyle.Bold);
            lbl.AutoSize = true;
            lbl.Location = new Point(18, 14);
            lbl.ForeColor = Color.FromArgb(150, 220, 255);
            this.Controls.Add(lbl);

            BodyBox = new TextBox();
            BodyBox.Multiline = true;
            BodyBox.ReadOnly = true;
            BodyBox.ScrollBars = ScrollBars.Both;
            BodyBox.WordWrap = false;
            BodyBox.BackColor = Color.FromArgb(20, 20, 20);
            BodyBox.ForeColor = Color.FromArgb(220, 220, 220);
            BodyBox.BorderStyle = BorderStyle.None;
            BodyBox.Font = new Font("Consolas", 10.5f);
            BodyBox.Location = new Point(18, 48);
            BodyBox.Size = new Size(944, 540);
            BodyBox.Text = text;
            this.Controls.Add(BodyBox);

            var ok = new Button();
            ok.Text = "OK  -  approve and start the stages";
            ok.Location = new Point(18, 604);
            ok.Size = new Size(320, 42);
            ok.Font = new Font("Segoe UI", 11f, FontStyle.Bold);
            ok.BackColor = Color.FromArgb(30, 110, 60);
            ok.ForeColor = Color.White;
            ok.FlatStyle = FlatStyle.Flat;
            ok.Click += delegate {
                this.Approved = true;
                this.Stamp = DateTime.Now;
                this.Close();
            };
            this.Controls.Add(ok);

            var no = new Button();
            no.Text = "No  -  stop here";
            no.Location = new Point(350, 604);
            no.Size = new Size(200, 42);
            no.Font = new Font("Segoe UI", 11f);
            no.BackColor = Color.FromArgb(90, 40, 40);
            no.ForeColor = Color.White;
            no.FlatStyle = FlatStyle.Flat;
            no.Click += delegate { this.Approved = false; this.Close(); };
            this.Controls.Add(no);

            this.CancelButton = no;
            this.FormClosing += delegate { if (this.Approved) this.Stamp = DateTime.Now; };
        }
    }
}
'@
}

# ---------------------------------------------------------------- BODY
$text = $Body
if ($DecisionsFile -and (Test-Path -LiteralPath $DecisionsFile)) {
    $doc = Get-Content -LiteralPath $DecisionsFile -Raw | ConvertFrom-Json
    $sb = New-Object System.Text.StringBuilder
    if ($doc.task) { [void]$sb.AppendLine("TASK"); [void]$sb.AppendLine(("  " + $doc.task)); [void]$sb.AppendLine() }
    if ($doc.scope) { [void]$sb.AppendLine("SCOPE"); [void]$sb.AppendLine(("  " + $doc.scope)); [void]$sb.AppendLine() }
    if ($doc.decisions) {
        [void]$sb.AppendLine('DECISIONS')
        $i = 1
        foreach ($d in $doc.decisions) {
            [void]$sb.AppendLine(("  {0}. {1}" -f $i, $d.decision))
            if ($d.because) { [void]$sb.AppendLine(("     because : " + $d.because)) }
            if ($d.cost)   { [void]$sb.AppendLine(("     cost    : " + $d.cost)) }
            if ($d.alt)    { [void]$sb.AppendLine(("     alt     : " + $d.alt)) }
            $i++
        }
        [void]$sb.AppendLine()
    }
    if ($doc.will_run) {
        [void]$sb.AppendLine('WHAT RUNS ON OK')
        foreach ($w in $doc.will_run) { [void]$sb.AppendLine(("  - " + $w)) }
        [void]$sb.AppendLine()
    }
    if ($doc.will_not_run) {
        [void]$sb.AppendLine('DELIBERATELY NOT RUNNING')
        foreach ($w in $doc.will_not_run) { [void]$sb.AppendLine(("  - " + $w)) }
        [void]$sb.AppendLine()
    }
    $text = $sb.ToString()
}

if (-not $text) { $text = '(nothing to review)' }

# ---------------------------------------------------------------- SHOW
try {
    $form = New-Object PipMon.ApproveForm($Title, $text)
    if ($TimeoutSec -gt 0) {
        $timer = New-Object System.Windows.Forms.Timer
        $timer.Interval = $TimeoutSec * 1000
        $timer.Add_Tick({ $form.Close() })
        $timer.Start()
        [void]$form.ShowDialog()
        $timer.Stop()
    } else {
        [void]$form.ShowDialog()
    }
} catch {
    Write-Output ("GUI unavailable: " + $_.Exception.Message)
    Write-Output 'falling back to the terminal. Approve with: tools\approve.ps1 -AutoApprove'
    exit 2
}

$stamp = if ($form.Stamp -eq [DateTime]::MinValue) { (Get-Date).ToString('o') } else { $form.Stamp.ToString('o') }
$logDir = Join-Path (Split-Path -Parent $PSScriptRoot) 'runs\watch'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$rec = [ordered]@{ approved = $form.Approved; stamp = $stamp; title = $Title; task = $text }
$rec | ConvertTo-Json -Depth 4 | Add-Content -LiteralPath (Join-Path $logDir 'approvals.jsonl') -Encoding utf8

if ($form.Approved) {
    Write-Output ("APPROVED at " + $stamp)
    exit 0
}
Write-Output ("DECLINED at " + $stamp)
exit 3

