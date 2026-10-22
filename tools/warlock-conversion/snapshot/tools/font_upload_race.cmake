if(TARGET font_upload_race)
  return()
endif()
add_executable(font_upload_race EXCLUDE_FROM_ALL
  "${CMAKE_CURRENT_LIST_DIR}/font_upload_race.cpp"
  "${CMAKE_SOURCE_DIR}/src/graphics/shared_memory.cpp"
  "${CMAKE_SOURCE_DIR}/src/graphics/pipeline/texture/cache.cpp"
  "${CMAKE_SOURCE_DIR}/src/graphics/flags.cpp"
  "${CMAKE_SOURCE_DIR}/src/graphics/register_file.cpp")
target_link_libraries(font_upload_race PRIVATE rexruntime)
target_include_directories(font_upload_race PRIVATE "${CMAKE_SOURCE_DIR}/include")
target_compile_features(font_upload_race PRIVATE cxx_std_23)
target_link_libraries(font_upload_race PRIVATE xxhash)
target_include_directories(font_upload_race PRIVATE "${CMAKE_SOURCE_DIR}/thirdparty/renderdoc")
