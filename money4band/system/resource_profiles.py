"""Interactive resource profile management (menu entry)."""

from __future__ import annotations

import os
from typing import Any

from colorama import Fore, Style, just_fix_windows_console

from money4band.core.dumper import write_json
from money4band.core.loader import load_json_config
from money4band.system import detector
from money4band.ui.cls import cls

just_fix_windows_console()


def _switch_profile(
    profile_name: str,
    m4b_config: dict[str, Any],
    m4b_config_path: str,
    app_config_path: str,
    user_config_path: str,
) -> dict[str, Any]:
    """Switch to *profile_name*, recalculate limits, regenerate .env."""
    user_config = load_json_config(user_config_path)
    user_config.setdefault("settings", {})["resource_profile"] = profile_name
    write_json(user_config, user_config_path)

    detector.calculate_resource_limits(user_config_path, m4b_config=m4b_config)

    from money4band.docker.generator import generate_env_file

    generate_env_file(
        m4b_config_path,
        app_config_path,
        user_config_path,
        env_output_path=os.path.join(os.path.dirname(m4b_config_path), os.pardir, ".env"),
    )
    return load_json_config(user_config_path)


def main(
    app_config_path: str,
    m4b_config_path: str,
    user_config_path: str,
) -> None:
    """Entry point when invoked from the interactive menu."""
    while True:
        cls()
        m4b_config = load_json_config(m4b_config_path)
        user_config = load_json_config(user_config_path)

        detector.show_resource_profile_info(m4b_config, user_config)

        valid = detector.get_valid_profiles(m4b_config)
        active = detector.get_active_profile(user_config)

        # Numbered profile picker
        print(f"\n  {Fore.CYAN}Switch profile:{Style.RESET_ALL}")
        for i, name in enumerate(valid, 1):
            marker = f" {Fore.GREEN}(active){Style.RESET_ALL}" if name == active else ""
            print(f"    {i}. {name}{marker}")
        print(
            f"\n  {Fore.CYAN}b{Style.RESET_ALL} Back  |  "
            f"{Fore.CYAN}q{Style.RESET_ALL} Quit"
        )

        choice = input("Select: ").strip().lower()

        if choice == "q":
            raise SystemExit(0)
        if choice == "b":
            break

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(valid):
                selected = valid[idx]
                if selected == active:
                    print(f"{Fore.YELLOW}Already on '{selected}'.{Style.RESET_ALL}")
                else:
                    user_config = _switch_profile(
                        selected, m4b_config, m4b_config_path,
                        app_config_path, user_config_path,
                    )
                    print(f"\n{Fore.GREEN}Switched to: {selected}{Style.RESET_ALL}")
                    print(
                        f"{Fore.YELLOW}Restart your stack (`m4b start`) "
                        f"for new limits to take effect.{Style.RESET_ALL}"
                    )
                input("\nPress Enter to continue...")
            else:
                print(f"{Fore.YELLOW}Invalid selection.{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.YELLOW}Invalid selection.{Style.RESET_ALL}")
