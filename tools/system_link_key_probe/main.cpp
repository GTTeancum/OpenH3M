#include <xtl.h>

#include <cstring>

extern "C" DWORD XeKeysHmacSha(DWORD key_number, const void* input_1,
                                DWORD input_1_size, const void* input_2,
                                DWORD input_2_size, const void* input_3,
                                DWORD input_3_size, void* output,
                                DWORD output_size);

extern "C" void XeCryptHmacSha(const void* key, DWORD key_size,
                                const void* input_1, DWORD input_1_size,
                                const void* input_2, DWORD input_2_size,
                                const void* input_3, DWORD input_3_size,
                                void* output, DWORD output_size);

namespace {

const BYTE kCandidateRetailKey[16] = {
    0xE1, 0xBC, 0x15, 0x9C, 0x73, 0xB1, 0xEA, 0xE9,
    0xAB, 0x31, 0x70, 0xF3, 0xAD, 0x47, 0xEB, 0xF3,
};

const BYTE kHalo3MythicLanKey[16] = {
    0x51, 0x55, 0xA4, 0xF8, 0x11, 0xC1, 0xE9, 0x19,
    0xE7, 0xD9, 0xA4, 0x7F, 0x16, 0xE0, 0x6C, 0xC9,
};

const BYTE kExpectedHalo3MythicAuthenticationDigest[20] = {
    0x24, 0xDE, 0xB6, 0xB8, 0xBA, 0x60, 0x01, 0xBA, 0x42, 0x52,
    0xFE, 0xA6, 0x6C, 0xBE, 0x1D, 0x9A, 0x0F, 0xF5, 0xDC, 0x01,
};

void ShowResult(const wchar_t* text, DWORD flags) {
  LPCWSTR buttons[] = {L"OK"};
  MESSAGEBOX_RESULT result = {};
  XOVERLAPPED overlapped = {};
  const DWORD status =
      XShowMessageBoxUI(XUSER_INDEX_ANY, L"OpenH3M System Link Probe", text,
                        1, buttons, 0, flags, &result, &overlapped);

  if (status == ERROR_IO_PENDING) {
    while (!XHasOverlappedIoCompleted(&overlapped)) {
      Sleep(33);
    }
  } else {
    // Keep immediate UI failures visible instead of returning to the dashboard.
    Sleep(10000);
  }
}

}  // namespace

int main() {
  BYTE input[17] = {};
  for (DWORD i = 0; i < sizeof(input); ++i) {
    input[i] = static_cast<BYTE>(i);
  }

  BYTE protected_digest[20] = {};
  BYTE candidate_digest[20] = {};
  const DWORD status = XeKeysHmacSha(0x19, input, sizeof(input), NULL, 0,
                                     NULL, 0, protected_digest,
                                     sizeof(protected_digest));
  if (status != ERROR_SUCCESS) {
    ShowResult(L"KEY 0x19 API ERROR", XMB_ERRORICON);
    return 1;
  }

  XeCryptHmacSha(kCandidateRetailKey, sizeof(kCandidateRetailKey), input,
                 sizeof(input), NULL, 0, NULL, 0, candidate_digest,
                 sizeof(candidate_digest));
  if (std::memcmp(protected_digest, candidate_digest,
                  sizeof(protected_digest)) == 0) {
    BYTE title_input[17] = {};
    BYTE title_digest[20] = {};
    std::memcpy(title_input + 1, kHalo3MythicLanKey,
                sizeof(kHalo3MythicLanKey));
    const DWORD title_status =
        XeKeysHmacSha(0x19, title_input, sizeof(title_input), NULL, 0, NULL, 0,
                      title_digest, sizeof(title_digest));
    if (title_status != ERROR_SUCCESS) {
      ShowResult(L"KEY 0x19: MATCH\nHALO LAN DERIVATION: API ERROR",
                 XMB_ERRORICON);
      return 3;
    }
    if (std::memcmp(title_digest, kExpectedHalo3MythicAuthenticationDigest,
                    sizeof(title_digest)) == 0) {
      ShowResult(L"KEY 0x19: MATCH\nHALO LAN DERIVATION: MATCH", XMB_NOICON);
      return 0;
    }

    ShowResult(L"KEY 0x19: MATCH\nHALO LAN DERIVATION: MISMATCH",
               XMB_WARNINGICON);
    return 4;
  }

  ShowResult(L"KEY 0x19: MISMATCH", XMB_WARNINGICON);
  return 2;
}
