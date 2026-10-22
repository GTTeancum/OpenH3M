# Add the game to the existing SDK build after SDK targets/helpers are defined.
# No second SDK build or copied SDK installation is needed.
function(openh3m_add_to_sdk)
  get_filename_component(_repo "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/../../../.." ABSOLUTE)
  set(REXGLUE_SHARE_DIR "${CMAKE_SOURCE_DIR}/src/ui")
  add_subdirectory("${_repo}/halo3mp" "${CMAKE_BINARY_DIR}/openh3m")
endfunction()
if(PROJECT_NAME STREQUAL "ReXGlue")
  openh3m_add_to_sdk()
endif()
