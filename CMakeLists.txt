cmake_minimum_required(VERSION 3.8)
project(lekiwi_bringup)

# find dependencies
find_package(ament_cmake REQUIRED)

# Install urdf files
install(DIRECTORY
  urdf
  launch
  rviz
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
