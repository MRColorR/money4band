from __future__ import annotations

import json
import logging
import os
import shutil


def reset_config(src_path: str, dest_path: str) -> None:
    """
    Resets a configuration file by copying from the source path to the destination path.

    Arguments:
    src_path -- the source file path
    dest_path -- the destination file path
    """
    try:
        logger = logging.getLogger(__name__)
        logger.info(
            f"Starting the process of resetting {os.path.basename(dest_path)}..."
        )

        if not os.path.exists(src_path):
            raise FileNotFoundError(f"Source file {src_path} does not exist.")

        dest_dir = os.path.dirname(dest_path)
        os.makedirs(dest_dir, exist_ok=True)

        shutil.copyfile(src_path, dest_path)
        logger.info(f"Successfully copied {src_path} to {dest_path}.")

        # Seed per-app slices from the catalog's user_config_template fields.
        # template/user-config.json intentionally has no per-app block;
        # every bundle declares its own default slice.
        _seed_app_slices_from_catalog(dest_path)

    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        raise
    except PermissionError as e:
        logger.error(f"Permission denied: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        raise


def _seed_app_slices_from_catalog(user_config_path: str) -> None:
    """Apply ``user_config_template`` defaults from the catalog into user-config.

    Loads the aggregated catalog via
    :func:`money4band.core.loader.load_app_config_with_overlays` (which
    reads the folded envelope from ``m4b-config.json`` plus the per-file
    bundles under ``config/catalog/``). Silently no-ops when the
    companion ``m4b-config.json`` cannot be located or parsed - the
    caller (reset) must remain resilient in unusual filesystem layouts
    (tests, custom installs).
    """
    logger = logging.getLogger(__name__)
    config_dir = os.path.dirname(user_config_path)
    m4b_config_path = os.path.join(config_dir, "m4b-config.json")
    if not os.path.exists(m4b_config_path):
        logger.debug(
            "Skipping user_config_template seed: %s not found", m4b_config_path
        )
        return
    try:
        with open(user_config_path, encoding="utf-8") as f:
            user_config = json.load(f)
        from money4band.core.loader import load_app_config_with_overlays

        app_config = load_app_config_with_overlays(m4b_config_path)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Skipping user_config_template seed: %s", exc)
        return

    from money4band.apps.user_config_merger import apply_user_config_templates

    added = apply_user_config_templates(user_config, app_config)
    if added:
        logger.info("Seeded %d app slice(s) from catalog templates.", added)

    with open(user_config_path, "w", encoding="utf-8") as f:
        json.dump(user_config, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main(
    app_config_path: str | None,
    m4b_config_path: str | None,
    user_config_path: str,
    src_path: str = "./template/user-config.json",
    dest_path: str = "./config/user-config.json",
) -> None:
    """
    Main function to call the reset_config function.

    Arguments:
    app_config_path -- unused; kept for menu dispatch call-site compatibility
    m4b_config_path -- unused; kept for menu dispatch call-site compatibility
    user_config_path -- the path to the user configuration file
    src_path -- the source file path
    dest_path -- the destination file path
    """
    reset_config(src_path=src_path, dest_path=dest_path)
