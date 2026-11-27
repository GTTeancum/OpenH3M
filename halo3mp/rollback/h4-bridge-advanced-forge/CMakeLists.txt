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
    src/video_quality.cpp
    src/video_quality_settings.cpp
    src/pc_video_settings.cpp
    src/pc_video_menu.cpp
)

if(WIN32)
    enable_language(RC)
    add_executable(halo3mp WIN32 ${HALO3MP_SOURCES})
    target_sources(halo3mp PRIVATE resources/spartan.rc)
    target_include_directories(halo3mp PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/resources")
else()
    add_executable(halo3mp ${HALO3MP_SOURCES})
endif()

rexglue_setup_target(halo3mp GPU_PLUGINS xenos)

# Explicit opt-in: Release optimization may still be used for developer builds.
option(OPENH3M_DEVELOPER_BUILD "Enable developer-only F7 rendering unlock" OFF)
if(OPENH3M_DEVELOPER_BUILD)
    target_compile_definitions(halo3mp PRIVATE OPENH3M_DEVELOPER_BUILD=1)
    target_sources(halo3mp PRIVATE src/developer_framerate.cpp)
    target_sources(halo3mp PRIVATE src/map_benchmark.cpp)
endif()

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

# Advanced Forge reuses original H4 code generated privately by ReXGlue.
# Keep it optional so an ordinary H3 build does not require Halo 4 assets.
option(OPENH3M_ADVANCED_FORGE "Build the original Halo 4 Forge bridge" OFF)
if(OPENH3M_ADVANCED_FORGE)
    set(_h4_tools "${CMAKE_CURRENT_SOURCE_DIR}/../tools/h4-forge")
    set(_h4_generated "${CMAKE_CURRENT_SOURCE_DIR}/../work/h4-forge-research/isolated")
    if(NOT WIN32 OR NOT EXISTS "${_h4_generated}/forge_original.cpp")
        message(FATAL_ERROR "Advanced Forge requires Windows and the private H4 ReXGlue extraction; see tools/h4-forge/README.md")
    endif()
    if(NOT EXISTS "${_h4_generated}/native_forge_tick.inl")
        message(FATAL_ERROR "Advanced Forge requires native tick extraction: run tools/h4-forge/extract_native_tick.py before configuring")
    endif()
    add_library(h4_forge_original STATIC
        "${_h4_tools}/forge_bridge.cpp"
        "${_h4_generated}/forge_original.cpp")
    target_include_directories(h4_forge_original PRIVATE "${_h4_generated}")
    target_include_directories(h4_forge_original PUBLIC "${_h4_tools}")
    target_link_libraries(h4_forge_original PRIVATE rex::runtime)
    target_link_libraries(halo3mp PRIVATE h4_forge_original)
    target_sources(halo3mp PRIVATE src/advanced_forge.cpp src/advanced_forge_pose_sync.cpp)
    target_compile_definitions(halo3mp PRIVATE OPENH3M_ADVANCED_FORGE=1)
    # Private local runtime inputs, kept beside this opt-in build so entering
    # Forge requires no external setting. Never add these assets to Git or the
    # public release package; that package requires a separate licensed-input flow.
    add_custom_target(h4_forge_runtime_data
        COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:halo3mp>/advanced-forge/isolated"
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${_h4_generated}/../h4-image.bin" "$<TARGET_FILE_DIR:halo3mp>/advanced-forge/h4-image.bin"
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${_h4_generated}/forge-globals.bin" "${_h4_generated}/camera-pitch-function.bin" "${_h4_generated}/camera-settings.bin" "${_h4_generated}/markers.bin" "${_h4_generated}/marker-material.bin"
            "$<TARGET_FILE_DIR:halo3mp>/advanced-forge/isolated"
        VERBATIM)
    add_dependencies(halo3mp h4_forge_runtime_data)
    add_executable(h4_forge_controls_check "${_h4_tools}/test_controls.cpp")
    target_link_libraries(h4_forge_controls_check PRIVATE imgui::imgui rex::runtime h4_forge_original)
    add_executable(h4_forge_bridge_check "${_h4_tools}/test_bridge.cpp")
    target_link_libraries(h4_forge_bridge_check PRIVATE h4_forge_original)
    add_executable(h4_forge_lzx_decode EXCLUDE_FROM_ALL "${_h4_tools}/decode_lzx_page.cpp")
    target_link_libraries(h4_forge_lzx_decode PRIVATE rex::runtime)
    add_executable(h4_forge_occlusion_check EXCLUDE_FROM_ALL "${_h4_tools}/test_occlusion_scopes.cpp")
    target_link_libraries(h4_forge_occlusion_check PRIVATE d3d12 d3dcompiler dxgi)
    add_executable(h4_forge_shader_disasm EXCLUDE_FROM_ALL "${_h4_tools}/disassemble_shader.cpp")
    target_sources(h4_forge_shader_disasm PRIVATE
        "${REXGLUE_ROOT}/src/graphics/format/ucode.cpp"
        "${REXGLUE_ROOT}/src/graphics/pipeline/shader/shader.cpp"
        "${REXGLUE_ROOT}/src/graphics/pipeline/shader/translator.cpp"
        "${REXGLUE_ROOT}/src/graphics/pipeline/shader/translator_disasm.cpp")
    target_link_libraries(h4_forge_shader_disasm PRIVATE rex::runtime)
    add_executable(h4_forge_marker_shader_check EXCLUDE_FROM_ALL "${_h4_tools}/check_marker_shader.cpp")
    target_sources(h4_forge_marker_shader_check PRIVATE
        "${REXGLUE_ROOT}/src/graphics/format/ucode.cpp"
        "${REXGLUE_ROOT}/src/graphics/register_file.cpp"
        "${REXGLUE_ROOT}/src/graphics/pipeline/shader/shader.cpp"
        "${REXGLUE_ROOT}/src/graphics/pipeline/shader/interpreter.cpp"
        "${REXGLUE_ROOT}/src/graphics/pipeline/shader/translator.cpp"
        "${REXGLUE_ROOT}/src/graphics/pipeline/shader/translator_disasm.cpp")
    target_link_libraries(h4_forge_marker_shader_check PRIVATE rex::runtime)
    add_executable(h4_forge_marker_shader_gpu EXCLUDE_FROM_ALL "${_h4_tools}/check_marker_shader_gpu.cpp")
    target_link_libraries(h4_forge_marker_shader_gpu PRIVATE d3d11 d3dcompiler)
    add_executable(h4_forge_marker_compile EXCLUDE_FROM_ALL "${_h4_tools}/compile_marker_material.cpp")
    target_include_directories(h4_forge_marker_compile PRIVATE "${REXGLUE_ROOT}/include")
    target_link_libraries(h4_forge_marker_compile PRIVATE d3dcompiler)
    add_executable(h4_forge_marker_pipeline_check EXCLUDE_FROM_ALL "${_h4_tools}/check_marker_pipeline.cpp")
    target_link_libraries(h4_forge_marker_pipeline_check PRIVATE d3d11)
endif()

# Small process-local check for the temporary F4 video controls.
if(TARGET rex::runtime AND DEFINED REXGLUE_ROOT AND EXISTS "${REXGLUE_ROOT}/src/ui/overlay/video_options.h")
    add_executable(video_settings_check EXCLUDE_FROM_ALL ../tools/video-options/test_settings.cpp)
    target_include_directories(video_settings_check PRIVATE "${REXGLUE_ROOT}/src/ui/overlay" "${REXGLUE_ROOT}/thirdparty/imgui")
    target_sources(video_settings_check PRIVATE src/video_quality_settings.cpp)
    target_include_directories(video_settings_check PRIVATE src)
    target_include_directories(halo3mp PRIVATE "${REXGLUE_ROOT}/src/ui/overlay")
    target_link_libraries(video_settings_check PRIVATE rex::runtime)
    add_executable(pc_video_settings_check EXCLUDE_FROM_ALL ../tools/video-options/test_pc_video.cpp
        src/pc_video_settings.cpp src/video_quality_settings.cpp)
    target_include_directories(pc_video_settings_check PRIVATE src "${REXGLUE_ROOT}/thirdparty/imgui")
    target_link_libraries(pc_video_settings_check PRIVATE rex::runtime)
endif()

if(TARGET rex::runtime AND WIN32)
    add_executable(input_focus_check EXCLUDE_FROM_ALL ../tools/input-focus/test_focus.cpp)
    target_include_directories(input_focus_check PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/../work/input-focus")
    target_link_libraries(input_focus_check PRIVATE rex::runtime)
endif()
