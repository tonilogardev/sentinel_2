"""QuickLook generation (8-bit RGB JPEG + 16-bit RGBNir COG)."""

from __future__ import annotations

from pathlib import Path

from s2_process.utils.cog_utils import quicklook_8bit, quicklook_16bit


def generate_quicklooks(
    input_mosaic: str | Path,
    output_dir: str | Path,
    scene_name: str,
    gdal_bin: str | Path,
) -> tuple[str, str]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 8-bit RGB JPEG COG
    rgb_name = f"S2_RGB_8b_{scene_name}.tif"
    rgb_path = str(output_dir / rgb_name)
    quicklook_8bit(gdal_bin, str(input_mosaic), rgb_path)

    # 16-bit RGBNir COG
    rgbn_name = f"S2_RGBI_16b_{scene_name}.btf"
    rgbn_path = str(output_dir / rgbn_name)
    quicklook_16bit(gdal_bin, str(input_mosaic), rgbn_path)

    return rgb_path, rgbn_path
