BS = chr(92)
NL = BS + "n"

p = r"C:\Programming\GitHub\Halo-3-MP\halo3mp\src\main.cpp"
s = open(p, encoding="utf-8").read()

old = (
    '      } else {' + "\n"
    '        std::fprintf(f, "  frame[%02u] ext=0x%llX' + NL + '", i,' + "\n"
    '                     static_cast<unsigned long long>(a));' + "\n"
    '      }'
)

new = (
    '      } else {' + "\n"
    '        char name[MAX_PATH] = "?";' + "\n"
    '        HMODULE hm = nullptr;' + "\n"
    '        if (GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |' + "\n"
    '                                   GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,' + "\n"
    '                               reinterpret_cast<LPCSTR>(a), &hm) &&' + "\n"
    '            hm) {' + "\n"
    '          GetModuleFileNameA(hm, name, MAX_PATH);' + "\n"
    '        }' + "\n"
    '        std::fprintf(f, "  frame[%02u] ext=0x%llX  %s+0x%llX' + NL + '", i,' + "\n"
    '                     static_cast<unsigned long long>(a), name,' + "\n"
    '                     static_cast<unsigned long long>(a - reinterpret_cast<uintptr_t>(hm)));' + "\n"
    '      }'
)

if old not in s:
    print("ANCHOR NOT FOUND")
    i = s.find("ext=0x")
    print(repr(s[i - 200:i + 200]))
    raise SystemExit(1)

s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("patched main.cpp with module names")
