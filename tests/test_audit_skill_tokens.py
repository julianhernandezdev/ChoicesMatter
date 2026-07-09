from scripts.audit_skill_tokens import derive_project_slug


# ---------------------------------------------------------------------------
# derive_project_slug
# ---------------------------------------------------------------------------

def test_derive_project_slug_backslash_path() -> None:
    assert derive_project_slug(r"D:\Project\ChoicesMatter") == "d--Project-ChoicesMatter"


def test_derive_project_slug_forward_slash_path() -> None:
    assert derive_project_slug("D:/Project/ChoicesMatter") == "d--Project-ChoicesMatter"


def test_derive_project_slug_lowercases_only_drive_letter() -> None:
    assert derive_project_slug(r"C:\Users\julia\SomeProject") == "c--Users-julia-SomeProject"
