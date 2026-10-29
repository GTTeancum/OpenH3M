# halo3mp - ReXGlue Recompiled Project
#
# SDK boilerplate lives in generated/rexglue.cmake.

cmake_minimum_required(VERSION 3.25)
project(halo3mp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(generated/rexglue.cmake)

# Sources
set(HALO3MP_SOURCES
    src/main.cpp
    src/fiber_switch.cpp
    src/local_user_hotpath.cpp
    src/system_link.cpp
)

if(WIN32)
    add_executable(halo3mp WIN32 ${HALO3MP_SOURCES})
else()
    add_executable(halo3mp ${HALO3MP_SOURCES})
endif()

rexglue_setup_target(halo3mp GPU_PLUGINS xenos)

# The application uses SDK ImGui UI headers directly when sharing its source build.
if(DEFINED REXGLUE_ROOT AND EXISTS "${REXGLUE_ROOT}/thirdparty/imgui/imgui.h")
    target_include_directories(halo3mp PRIVATE "${REXGLUE_ROOT}/thirdparty/imgui")
endif()

if(WIN32)
    target_link_libraries(halo3mp PRIVATE windowscodecs ole32 iphlpapi ws2_32)
endif()

# Cross-module (guest->guest) import thunks.
# ReXGlue v0.10 does not resolve guest DLL -> guest DLL function imports, so the
# l360/q10 modules declare WavesLibDLL thunks without bodies. Supply them here.
foreach(_rexmod l360 q10)
    if(TARGET halo3mp_${_rexmod})
        target_sources(halo3mp_${_rexmod} PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/src/${_rexmod}_import_stubs.cpp)
    endif()
endforeach()

if(TARGET rex::runtime AND WIN32)
    add_executable(input_focus_check EXCLUDE_FROM_ALL ../tools/input-focus/test_focus.cpp)
    target_include_directories(input_focus_check PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/../work/input-focus")
    target_link_libraries(input_focus_check PRIVATE rex::runtime)
endif()
