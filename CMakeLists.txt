cmake_minimum_required(VERSION 3.20)

# WWE WrestleMania 21, statically recompiled on the xboxrecomp toolkit.
#
# Build with scripts/build.py, which lifts the game first. The generated
# sources in src/recomp/gen/ come from your own copy of the game and are
# never committed.

project(wwe21_recomp C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

add_compile_definitions(
    WIN32_LEAN_AND_MEAN
    NOMINMAX
)

set(XBOXRECOMP_DIR "${CMAKE_CURRENT_SOURCE_DIR}/xboxrecomp" CACHE PATH
    "Path to the xboxrecomp toolkit (the submodule by default)")

if(NOT EXISTS "${XBOXRECOMP_DIR}/CMakeLists.txt")
    message(FATAL_ERROR "xboxrecomp not found at ${XBOXRECOMP_DIR}. "
        "Run: git submodule update --init --recursive")
endif()

# Checks that every call preserves ebx/esi/edi and esp. Set before
# add_subdirectory: the check is emitted into the generated game code but
# its logger lives in xbox_kernel. See the toolkit's templates/new-game.
option(RECOMP_ABI_CHECK "Verify callee-saved registers across every call" OFF)
if(RECOMP_ABI_CHECK)
    add_compile_definitions(RECOMP_ABI_CHECK)
endif()

add_subdirectory(${XBOXRECOMP_DIR} ${CMAKE_BINARY_DIR}/xboxrecomp)

# CONFIGURE_DEPENDS so a re-lift that adds or removes a chunk is picked up
# without a manual re-configure.
file(GLOB RECOMP_GEN_SOURCES CONFIGURE_DEPENDS "src/recomp/gen/*.c")
if(NOT RECOMP_GEN_SOURCES)
    message(FATAL_ERROR "No generated sources in src/recomp/gen. "
        "Lift the game first: py -3 scripts/build.py")
endif()

add_executable(${PROJECT_NAME}
    src/main.c
    src/recomp_manual.c
    ${RECOMP_GEN_SOURCES}
)
# A windowed program on Windows (WinMain, no console); a plain executable
# elsewhere, whose main() hands the game its own thread (host_main_posix).
if(WIN32)
    set_target_properties(${PROJECT_NAME} PROPERTIES WIN32_EXECUTABLE ON)
endif()

target_link_libraries(${PROJECT_NAME} PRIVATE xboxrecomp)

target_include_directories(${PROJECT_NAME} PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${CMAKE_CURRENT_SOURCE_DIR}/src/recomp
    ${XBOXRECOMP_DIR}/include
)

# Off Windows the runtime libraries bring their own host libraries (pthreads,
# dl, SDL3, OpenSSL).
if(WIN32)
    target_link_libraries(${PROJECT_NAME} PRIVATE
        d3d11
        dxgi
        dxguid
        xinput
        winmm
        dbghelp     # lets the crash handler name the generated function that faulted
    )
else()
    # The POSIX fault report names a host pc with dladdr, which sees only
    # exported symbols: export the generated functions.
    set_target_properties(${PROJECT_NAME} PROPERTIES ENABLE_EXPORTS ON)
endif()

if(MSVC)
    # /DEBUG: a PDB in every configuration, so a crash names sub_XXXXXXXX.
    target_link_options(${PROJECT_NAME} PRIVATE /LARGEADDRESSAWARE /DEBUG)
    target_compile_options(${PROJECT_NAME} PRIVATE /bigobj /MP)
    # Lifted code reads ebp before writing it by design (fpo_leaf functions
    # inherit the caller's frame), which /RTC1 aborts on through a message box.
    string(REGEX REPLACE "/RTC[1csu]+" "" CMAKE_C_FLAGS_DEBUG "${CMAKE_C_FLAGS_DEBUG}")
endif()

# WrestleMania 21 has no 16:9 mode of its own (CreateDevice gets no widescreen
# flag with the console's set), so widescreen means Hor+: every vertex program
# it draws the world with, skinned or not, takes oPos from dp4 with c96..c99,
# the model-view-projection, and the toolkit scales c96 on screen draws.
if(COMMAND recomp_title_widescreen)
    recomp_title_widescreen(HOR_PLUS REGISTER 96)
endif()

# The settings window: video options, input bindings, then starts the game.
if(COMMAND recomp_add_launcher)
    recomp_add_launcher(${PROJECT_NAME}_launcher ${PROJECT_NAME}.exe)
endif()
