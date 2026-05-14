try:
    from pip._vendor.pkg_resources import *
except ImportError as exc:
    raise ImportError(
        "pkg_resources is required by razorpay but was not found in the environment. "
        "Ensure the application is launched from the project venv and that pip/setuptools are installed."
    ) from exc
