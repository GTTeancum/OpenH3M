# Spartan executable icon

`spartan.png` is the transparent master; `spartan.ico` contains 16, 24, 32,
48, 64, 128 and 256 pixel sizes. `spartan.rc` embeds it as Windows icon 1.

Source supplied by the user on 2026-11-03:
https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTSUz_EI5s8ESfKYDy3bosz7oaSlaXRDqYTrXHRUE6ChKwcK2IEGq3LEZk&s=10

Edited with the built-in image generation tool, then packaged as ICO with Pillow.
Prompt: Crop to the existing Spartan bust, keeping the entire helmet, shoulders
and chest visible. Remove the white background to actual alpha transparency,
including white gaps around the silhouette. Preserve the source character,
low-poly game-render style, olive armor, gold visor, pose, textures and proportions;
do not redesign or add detail. Center on a square transparent canvas with a narrow
safe margin. No text, border, shadow or painted checkerboard.

Verified alpha transparency in every ICO size and successful compilation with
Windows SDK 10.0.26100.0 rc.exe. Existing runtime executables were not replaced.

User framing revision: helmet to the tops of the shoulders only. Final built-in
edit prompt tightened the crop to the full helmet and chin, with just the shoulder
tops at the bottom corners, removing chest plates and lower straps. Preserve
character colors, materials and pose, with actual transparency around the helmet.
