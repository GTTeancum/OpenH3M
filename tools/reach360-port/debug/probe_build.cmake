# REXGLUE_EXTERNAL_PROJECTS_FILE for a separate ReXGlue SDK build that adds the game with the collision probe hooks.
# The game source (generated recompiled code + host sources) is used read-only from the existing workspace.
set(OPENH3M_GAME_SOURCE "C:/X360/ISOs/H3M/.local/OpenH3M-source/halo3mp" CACHE PATH "game project used read-only")
set(REXGLUE_SHARE_DIR "${CMAKE_SOURCE_DIR}/src/ui")
add_subdirectory("${OPENH3M_GAME_SOURCE}" "${CMAKE_BINARY_DIR}/openh3m")
target_sources(halo3mp PRIVATE "${CMAKE_CURRENT_LIST_DIR}/collision_probe.cpp")

# The SDK pins every output to its source tree's out/<platform> (the installed build). Redirect all targets of this
# build into its own folder so it can never overwrite the installed game.
function(reach360_redirect dir)
  get_property(targets DIRECTORY "${dir}" PROPERTY BUILDSYSTEM_TARGETS)
  foreach(t ${targets})
    get_target_property(type ${t} TYPE)
    if(NOT type STREQUAL "INTERFACE_LIBRARY" AND NOT type STREQUAL "UTILITY")
      set_target_properties(${t} PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/out"
        LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/out" ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/out")
    endif()
  endforeach()
  get_property(subs DIRECTORY "${dir}" PROPERTY SUBDIRECTORIES)
  foreach(s ${subs})
    reach360_redirect("${s}")
  endforeach()
endfunction()
reach360_redirect("${CMAKE_SOURCE_DIR}")

# Debug wireframe switch (--d3d12_debug_wireframe=true): every ordinary draw is rasterised as wireframe with a
# constant white pixel shader, so the screen shows exactly the triangles the game submits, unlit, on black.
# Full-screen passes (rectangle/quad/point lists, which go through a geometry shader) keep their own shaders so the
# composite still reaches the screen. The game's culling is untouched. The SDK source is read, patched here at
# configure time and compiled in place of the original; the SDK tree itself is never modified.
set(REACH360_PIPELINE_SRC "${CMAKE_SOURCE_DIR}/src/graphics/d3d12/pipeline_cache.cpp")
set(REACH360_PIPELINE_OUT "${CMAKE_BINARY_DIR}/reach360/pipeline_cache_wireframe.cpp")
file(READ "${REACH360_PIPELINE_SRC}" _pc)
set(_anchor1 "\"Render tessellation as wireframe\");")
set(_anchor2 "  // Geometry shader.\n  if (runtime_description.geometry_shader != nullptr) {")
set(_anchor3 "description.fill_mode_wireframe ? D3D12_FILL_MODE_WIREFRAME")
set(_anchor4 "  // Disable rasterization if needed")
set(_anchor5 "  PipelineDescription& description = runtime_description.description;
")
foreach(a _anchor1 _anchor2 _anchor3 _anchor4 _anchor5)
  string(FIND "${_pc}" "${${a}}" _pos)
  if(_pos EQUAL -1)
    message(FATAL_ERROR "reach360 wireframe patch: anchor ${a} not found in ${REACH360_PIPELINE_SRC}")
  endif()
endforeach()
file(READ "${CMAKE_CURRENT_LIST_DIR}/wireframe_white_ps.inc" _ps)
string(REPLACE "${_anchor1}" "${_anchor1}\n${_ps}" _pc "${_pc}")
string(REPLACE "${_anchor2}" "  const bool reach360_debug_wire =
      REXCVAR_GET(d3d12_debug_wireframe) && runtime_description.geometry_shader == nullptr &&
      (!(REXCVAR_GET(d3d12_debug_wireframe_flags) & 16) || description.depth_func != xenos::CompareFunction::kAlways);
  if (reach360_debug_wire && runtime_description.pixel_shader != nullptr && !edram_rov_used &&
      !Reach360WhitePixelShader().empty()) {
    state_desc.PS.pShaderBytecode = Reach360WhitePixelShader().data();
    state_desc.PS.BytecodeLength = Reach360WhitePixelShader().size();
  } else if (REXCVAR_GET(d3d12_debug_wireframe) && (REXCVAR_GET(d3d12_debug_wireframe_flags) & 4) &&
             description.geometry_shader == PipelineGeometryShader::kRectangleList &&
             description.render_targets[0].used &&
             description.render_targets[0].format == xenos::ColorRenderTargetFormat::k_16_16_16_16_FLOAT &&
             runtime_description.pixel_shader != nullptr && !Reach360BlackPixelShader().empty()) {
    // Bloom chain (full-screen passes into 16-bit float targets) is zeroed so dense wires cannot bloom into a fill.
    state_desc.PS.pShaderBytecode = Reach360BlackPixelShader().data();
    state_desc.PS.BytecodeLength = Reach360BlackPixelShader().size();
  }
${_anchor2}" _pc "${_pc}")
string(REPLACE "${_anchor3}" "(description.fill_mode_wireframe || reach360_debug_wire) ? D3D12_FILL_MODE_WIREFRAME" _pc "${_pc}")
# Wires overwrite instead of blending, so overlapping additive/transparent layers cannot accumulate into a white fill.
string(REPLACE "${_anchor4}" "  if (reach360_debug_wire) {
    if (REXCVAR_GET(d3d12_debug_wireframe_flags) & 1)
      for (auto& reach360_rt : state_desc.BlendState.RenderTarget) reach360_rt.BlendEnable = FALSE;
  } else if (REXCVAR_GET(d3d12_debug_wireframe) && (REXCVAR_GET(d3d12_debug_wireframe_flags) & 2)) {
    // Full-screen passes that blend onto the scene (fog, light shafts, overlays) are dropped; passes that overwrite
    // (tone mapping, bloom, the final composite) stay so the frame still reaches the screen.
    bool reach360_blends = false;
    for (auto& reach360_rt : state_desc.BlendState.RenderTarget) reach360_blends |= reach360_rt.BlendEnable != FALSE;
    if (reach360_blends) {
      for (auto& reach360_rt : state_desc.BlendState.RenderTarget) reach360_rt.RenderTargetWriteMask = 0;
    }
  }
${_anchor4}" _pc "${_pc}")
# One-frame draw log (--d3d12_debug_draw_log_frame=N): pass structure of a frame, one line per draw.
string(REPLACE "${_anchor5}" "${_anchor5}  if (REXCVAR_GET(d3d12_debug_draw_count)) {
    uint64_t f = command_processor_.GetCurrentFrame();
    if (f != reach360_count_frame) {
      if ((reach360_count_frame % 30) == 0)
        REXGPU_INFO(\"[drawcount] frame={} draws={} scene={}\", reach360_count_frame, reach360_count_all, reach360_count_scene);
      reach360_count_frame = f; reach360_count_all = 0; reach360_count_scene = 0;
    }
    ++reach360_count_all;
    if (description.geometry_shader == PipelineGeometryShader::kNone && description.pixel_shader_hash &&
        description.render_targets[0].used && description.render_targets[0].write_mask && description.depth_write)
      ++reach360_count_scene;
  }
  if (REXCVAR_GET(d3d12_debug_draw_log_frame) &&
      command_processor_.GetCurrentFrame() == REXCVAR_GET(d3d12_debug_draw_log_frame)) {
    std::string reach360_rts;
    for (uint32_t i = 0; i < 4; ++i) {
      const auto& rt = description.render_targets[i];
      if (!rt.used) continue;
      reach360_rts += fmt::format(\" rt{}:info={:08X},fmt={},mask={:X},blend={}/{}/{}\", i,
          register_file_[reg::RB_COLOR_INFO::rt_register_indices[i]], uint32_t(rt.format), uint32_t(rt.write_mask),
          uint32_t(rt.src_blend), uint32_t(rt.dest_blend), uint32_t(rt.blend_op));
    }
    REXGPU_INFO(\"[drawlog] vs={:016X} ps={:016X} gs={} prim={} cull={} depth={:08X} zfunc={} zw={} surf={:08X}{}\",
        description.vertex_shader_hash, description.pixel_shader_hash, uint32_t(description.geometry_shader),
        uint32_t(description.primitive_topology_type_or_tessellation_mode), uint32_t(description.cull_mode),
        register_file_[XE_GPU_REG_RB_DEPTH_INFO], uint32_t(description.depth_func), uint32_t(description.depth_write),
        register_file_[XE_GPU_REG_RB_SURFACE_INFO], reach360_rts);
  }
" _pc "${_pc}")
file(WRITE "${REACH360_PIPELINE_OUT}.tmp" "${_pc}")
file(COPY_FILE "${REACH360_PIPELINE_OUT}.tmp" "${REACH360_PIPELINE_OUT}" ONLY_IF_DIFFERENT)
set_property(DIRECTORY "${CMAKE_SOURCE_DIR}" APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
  "${REACH360_PIPELINE_SRC}" "${CMAKE_CURRENT_LIST_DIR}/wireframe_white_ps.inc")
get_target_property(_srcs rexgpu-xenos SOURCES)
list(REMOVE_ITEM _srcs "d3d12/pipeline_cache.cpp" "${CMAKE_SOURCE_DIR}/src/graphics/d3d12/pipeline_cache.cpp")
list(APPEND _srcs "${REACH360_PIPELINE_OUT}")
set_property(TARGET rexgpu-xenos PROPERTY SOURCES ${_srcs})
target_include_directories(rexgpu-xenos PRIVATE "${CMAKE_SOURCE_DIR}/src/graphics/d3d12")

# Debug wireframe, part 2: Halo 3 never clears its colour targets (sky and walls cover every pixel), so in wireframe
# almost every pixel would show stale frames. With the switch on, each colour target is cleared to black the first
# time it is bound in a frame. Same configure-time patch-and-swap as above, for render_target_cache.cpp.
set(REACH360_RTC_SRC "${CMAKE_SOURCE_DIR}/src/graphics/d3d12/render_target_cache.cpp")
set(REACH360_RTC_OUT "${CMAKE_BINARY_DIR}/reach360/render_target_cache_wireframe.cpp")
file(READ "${REACH360_RTC_SRC}" _rc)
set(_ranchor "  // Bind the render targets.\n  if (are_current_command_list_render_targets_valid_ &&")
string(FIND "${_rc}" "${_ranchor}" _pos)
if(_pos EQUAL -1)
  message(FATAL_ERROR "reach360 wireframe patch: bind anchor not found in ${REACH360_RTC_SRC}")
endif()
string(REPLACE "${_ranchor}" "  if (REXCVAR_GET(d3d12_debug_wireframe)) {
    static uint64_t reach360_frame = 0;
    static std::vector<const RenderTarget*> reach360_cleared;
    const uint64_t f = command_processor_.GetCurrentFrame();
    if (f != reach360_frame) { reach360_frame = f; reach360_cleared.clear(); }
    for (uint32_t i = 0; i < xenos::kMaxColorRenderTargets; ++i) {
      const RenderTarget* rt = depth_and_color_render_targets[1 + i];
      if (!rt || std::find(reach360_cleared.begin(), reach360_cleared.end(), rt) != reach360_cleared.end()) continue;
      reach360_cleared.push_back(rt);
      static const float reach360_black[4] = {0.0f, 0.0f, 0.0f, 0.0f};
      command_processor_.SubmitBarriers();
      command_processor_.GetDeferredCommandList().D3DClearRenderTargetView(
          static_cast<const D3D12RenderTarget*>(rt)->descriptor_draw().GetHandle(), reach360_black, 0, nullptr);
    }
  }
${_ranchor}" _rc "${_rc}")
string(REPLACE "#include \"sky_stage_probe.h\"" "#include \"sky_stage_probe.h\"\nREXCVAR_DECLARE(bool, d3d12_debug_wireframe);" _rc "${_rc}")
file(WRITE "${REACH360_RTC_OUT}.tmp" "${_rc}")
file(COPY_FILE "${REACH360_RTC_OUT}.tmp" "${REACH360_RTC_OUT}" ONLY_IF_DIFFERENT)
set_property(DIRECTORY "${CMAKE_SOURCE_DIR}" APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${REACH360_RTC_SRC}")
get_target_property(_srcs rexgpu-xenos SOURCES)
list(REMOVE_ITEM _srcs "d3d12/render_target_cache.cpp" "${REACH360_RTC_SRC}")
list(APPEND _srcs "${REACH360_RTC_OUT}")
set_property(TARGET rexgpu-xenos PROPERTY SOURCES ${_srcs})
