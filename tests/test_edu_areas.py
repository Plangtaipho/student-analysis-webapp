from fastapi.testclient import TestClient

from app.main import app


def test_area_list_has_all_245_offices():
    areas = TestClient(app).get("/api/edu/areas").json()
    assert len(areas) == 245
    assert sum(a["kind"] == "p" for a in areas) == 183 and sum(a["kind"] == "s" for a in areas) == 62
    assert {"name": "สำนักงานเขตพื้นที่การศึกษามัธยมศึกษาเลย หนองบัวลำภู", "short": "สพม.เลย หนองบัวลำภู", "kind": "s"} in areas


def test_schools_of_an_area():
    c = TestClient(app)
    r = c.get("/api/edu/schools", params={"area": "สำนักงานเขตพื้นที่การศึกษามัธยมศึกษาเลย หนองบัวลำภู"})
    assert r.status_code == 200 and "โรงเรียนหนองสวรรค์วิทยาคาร" in r.json()
    assert c.get("/api/edu/schools", params={"area": "ไม่มีเขตนี้"}).status_code == 404
