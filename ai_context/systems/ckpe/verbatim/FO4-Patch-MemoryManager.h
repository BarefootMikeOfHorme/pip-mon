---
source_url: https://raw.githubusercontent.com/Perchik71/Creation-Kit-Platform-Extended/master/CKPE.Fallout4/Include/Patches/CKPE.Fallout4.Patch.MemoryManager.h
retrieved_utc: 2026-09-30T21:53:23Z
content_kind: upstream-verbatim
trust: "Verbatim third-party C++ header, unmodified."
---

// Copyright © 2023-2025 aka CKPE team. All rights reserved.
// Contacts: <email:timencevaleksej@gmail.com>
// License: https://www.gnu.org/licenses/lgpl-3.0.html

#pragma once

#include <CKPE.Common.Patch.h>

namespace CKPE
{
	namespace Fallout4
	{
		namespace Patch
		{
			class MemoryManager : public Common::Patch
			{
				MemoryManager(const MemoryManager&) = delete;
				MemoryManager& operator=(const MemoryManager&) = delete;
			protected:
				virtual bool DoActive(Common::RelocatorDB::PatchDB* db) noexcept(true);
				virtual bool DoQuery() const noexcept(true);
			public:
				MemoryManager();

				virtual bool HasOption() const noexcept(true);
				virtual const char* GetOptionName() const noexcept(true);
				virtual bool HasDependencies() const noexcept(true);
				virtual std::vector<std::string> GetDependencies() const noexcept(true);

				static bool LowMemory() noexcept(true);
				[[nodiscard]] bool SupportsAddressLibrary() const noexcept(true) override { return true; }
			};
		}
	}
}