"""
MHN ARCADE V4 bootstrap guard.

V4 is not a production Discord release yet.
This guard prevents accidental startup before the adapter,
process supervision, and deployment configuration are ready.
"""


def main() -> None:

    raise SystemExit(
        "MHN ARCADE V4 is under construction. "
        "Keep the production app on v3-engine."
    )


if __name__ == "__main__":
    main()
