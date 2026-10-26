"""Real Streamlit execution tests for form wiring and rerun persistence."""
from datetime import date
from streamlit.testing.v1 import AppTest


def button(app, label):
    return next(element for element in app.button if element.label == label)


def text(app, label):
    return next(element for element in app.text_input if element.label == label)


def test_add_pet_task_edit_complete_and_reload(tmp_path, monkeypatch):
    path = tmp_path / "household.json"
    monkeypatch.setenv("PAWPAL_DATA_PATH", str(path))
    app = AppTest.from_file("app.py", default_timeout=15).run()
    assert not app.exception
    text(app, "Owner name").set_value("Alex")
    button(app, "Save owner").click().run()
    text(app, "Pet name").set_value("Buddy")
    button(app, "Add pet").click().run()
    assert not app.exception
    text(app, "Activity").set_value("Morning walk")
    next(element for element in app.selectbox if element.label == "Repeat").select("daily")
    button(app, "Schedule task").click().run()
    assert not app.exception
    assert len(app.session_state.owner.get_all_tasks()) == 1
    # Edit the task through the form rather than mutating backend state.
    activities = [element for element in app.text_input if element.label == "Activity"]
    activities[1].set_value("Updated walk")
    button(app, "Save changes").click().run()
    assert app.session_state.owner.get_all_tasks()[0].description == "Updated walk"
    button(app, "Generate schedule").click().run()
    assert any("fit without overlapping" in element.value for element in app.success)
    button(app, "Complete").click().run()
    assert not app.exception
    assert len(app.session_state.owner.get_all_tasks()) == 2
    assert app.session_state.owner.get_all_tasks()[0].completed
    fresh = AppTest.from_file("app.py", default_timeout=15).run()
    assert not fresh.exception
    assert fresh.session_state.owner.name == "Alex"
    assert len(fresh.session_state.owner.get_all_tasks()) == 2
    assert fresh.session_state.owner.get_all_tasks()[1].due.date() > date.today()


def test_invalid_input_and_sample_plan(tmp_path, monkeypatch):
    monkeypatch.setenv("PAWPAL_DATA_PATH", str(tmp_path / "sample.json"))
    app = AppTest.from_file("app.py", default_timeout=15).run()
    button(app, "Add pet").click().run()
    assert any("cannot be empty" in error.value for error in app.error)
    button(app, "Load sample household").click().run()
    assert not app.exception
    assert len(app.session_state.owner.pets) == 2
    assert any("overlaps" in warning.value for warning in app.warning)
    button(app, "Generate schedule").click().run()
    assert not app.exception
    assert any("4 task(s) fit" in success.value for success in app.success)
