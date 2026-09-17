from pywinauto import Desktop


def main():
    windows = Desktop(backend="uia").windows()

    for window in windows:
        try:
            process_id = window.process_id()
            title = window.window_text()

            if title:
                print(
                    f"PID: {process_id} | "
                    f"Title: {title!r} | "
                    f"Control: {window.element_info.control_type}"
                )

        except Exception:
            continue


if __name__ == "__main__":
    main()