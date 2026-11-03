Sky Bridge shader initialization load fix

First native launch26 failed at107.6s, before captures, with9 hash checks passed and0 failed. Fault in memcpy sub_825A4230 came from vertex shader initializer sub_825B9480, called by tag shader initialization sub_821A9B78. The initializer saves header+16 code pointer, clears872 runtime bytes, then copies vertex fetch records from code+offset. Reinitializing a shared header therefore reads from zero.

Static cache audit finds24 duplicated vertex headers across cloned glvs tags; stock Zanzibar has0. bind_soft_vertices replaced9 programs but shared untouched program headers with its donor and other clones. It now clones each untouched header plus relative debug data, preserving code pointer/code bytes/reflection/entry mappings. Replacement program headers were already private. Build27 will verify header uniqueness in the resulting cache before any load retry. Original failed payload26 is preserved.

Source: Sky Bridge, Halo Online; General Heed / Priception, Halo Online Map Pack For Halo3: https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190. This project supplies Xbox360/OpenH3M adaptation.
