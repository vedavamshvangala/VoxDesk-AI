from app.core.agent import AXE


def main():
    print("====================================")
    print("          AXE Desktop Agent")
    print("====================================")
    print("AXE is ready.")
    print("Type 'exit' to stop.")
    print()

    axe = AXE()

    while axe.session_active:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in {
                "exit",
                "quit",
                "bye",
            }:
                print("AXE: Goodbye.")
                break

            response = axe.respond(user_input)

            print(f"AXE: {response}")
            print()

        except KeyboardInterrupt:
            print()
            print("AXE: Goodbye.")
            break

        except Exception as exc:
            print(
                "AXE: I encountered an unexpected error: "
                f"{exc}"
            )


if __name__ == "__main__":
    main()