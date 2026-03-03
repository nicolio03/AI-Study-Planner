from pyicloud import PyiCloudService
import ipywidgets as widgets
from typing import Dict, Optional
from IPython.display import display

def start_icloud_login() -> Dict[str, Optional[PyiCloudService]]:

    email_box = widgets.Text(
            description="Apple ID:",
            placeholder="you@icloud.com",
            layout=widgets.Layout(width="450px"),
        )
    pass_box = widgets.Password(
        description="Password:",
        layout=widgets.Layout(width="450px"),
    )
    code_box = widgets.Text(
        description="2FA Code:",
        placeholder="6-digit code",
        layout=widgets.Layout(width="250px"),
    )
    login_btn = widgets.Button(description="Login", button_style="primary")
    code_btn = widgets.Button(description="Submit 2FA", button_style="warning")
    out = widgets.Output()

    code_box.layout.display = "none"
    code_btn.layout.display = "none"

    display(email_box, pass_box, login_btn, code_box, code_btn, out)

    state: Dict[str, Optional[PyiCloudService]] = {"api": None}

    def show_2fa_ui(show: bool):
        code_box.layout.display = "block" if show else "none"
        code_btn.layout.display = "inline-flex" if show else "none"


    def do_login(_):
        with out:
            out.clear_output()
            try:
                api = PyiCloudService(email_box.value.strip(), pass_box.value)
                state["api"] = api

                if api.requires_2fa:
                    show_2fa_ui(True)
                    print("Enter the 6-digit code in the 2FA box, then click 'Submit 2FA'.")
                else:
                    show_2fa_ui(False)
                    print("Logged in (no 2FA prompt).")

            except Exception:
                traceback.print_exc()

    def submit_2fa(_):
        with out:
            out.clear_output()
            api = state["api"]
            if api is None:
                print("Click Login first.")
                return

            code = code_box.value.strip()
            if not code:
                print("Enter the 6-digit code first.")
                return

            try:
                ok = api.validate_2fa_code(code)
                print("2FA code accepted:", ok)

                if ok and not api.is_trusted_session:
                    print("Trusting session...")
                    print("trusted:", api.trust_session())

                print("is_trusted_session:", api.is_trusted_session)

            except Exception:
                traceback.print_exc()

    login_btn.on_click(do_login)
    code_btn.on_click(submit_2fa)

    return state