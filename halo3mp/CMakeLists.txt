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
)

if(WIN32)
    add_executable(halo3mp WIN32 ${HALO3MP_SOURCES})
else()
    add_executable(halo3mp ${HALO3MP_SOURCES})
endif()

rexglue_setup_target(halo3mp GPU_PLUGINS xenos)

# Cross-module (guest->guest) import thunks.
# ReXGlue v0.10 does not resolve guest DLL -> guest DLL function imports, so the
# l360/q10 modules declare WavesLibDLL thunks without bodies. Supply them here.
foreach(_rexmod l360 q10)
    if(TARGET halo3mp_${_rexmod})
        target_sources(halo3mp_${_rexmod} PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/src/${_rexmod}_import_stubs.cpp)
    endif()
endforeach()
