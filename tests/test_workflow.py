"""The end-to-end workflow: upload → analyse → clip → thumbnail → copy → download."""
from __future__ import annotations


def test_upload_probes_the_file(uploaded_video):
    _client, _proj, video = uploaded_video
    assert video["duration_s"] > 5
    assert video["width"] == 640 and video["height"] == 360
    assert video["has_audio"] is True
    assert video["status"] == "uploaded"


def test_analyse_finds_moments_and_reports_transcript_honestly(uploaded_video):
    client, _proj, video = uploaded_video
    r = client.post(f"/api/videos/{video['id']}/analyse",
                    params={"sync": True, "clip_seconds": 5, "count": 3})
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "succeeded", body.get("error")
    moments = body["output"]["moments"]
    assert moments, "expected at least one suggested moment"
    for m in moments:
        assert m["end"] > m["start"]
        assert "Measured from the audio track" in m["reason"]
    # No ASR, no sidecar, no pasted text: the app must say so rather than invent speech.
    assert body["output"]["transcript_source"] == "none"


def test_full_workflow_produces_a_downloadable_clip_with_captions(uploaded_video):
    client, _proj, video = uploaded_video
    vid = video["id"]

    analysed = client.post(f"/api/videos/{vid}/analyse",
                           params={"sync": True, "clip_seconds": 5, "count": 2}).json()
    moment = analysed["output"]["moments"][0]

    # A pasted transcript turns captions on.
    r = client.post(f"/api/videos/{vid}/transcript", json={
        "text": "I kept losing the first three seconds. Then I measured the audio instead "
                "of guessing, and the hook finally landed. Here is the exact change.",
        "language": "en"})
    assert r.status_code == 200
    assert r.json()["transcript"]["source"] == "manual"

    r = client.post("/api/clips", params={"sync": True}, json={
        "video_id": vid, "start_s": moment["start"], "end_s": moment["end"],
        "title": "Hook test", "platform": "youtube_shorts"})
    assert r.status_code == 202, r.text
    assert r.json()["status"] == "succeeded", r.json().get("error")
    clip_id = r.json()["output"]["clips"][0]["clip_id"]

    clip = client.get(f"/api/clips/{clip_id}").json()
    assert clip["status"] == "ready"
    assert clip["has_subtitles"] is True
    assert clip["file_size"] > 0

    download = client.get(f"/api/clips/{clip_id}/download")
    assert download.status_code == 200
    assert len(download.content) > 10_000
    assert download.headers["content-type"] == "video/mp4"

    subs = client.get(f"/api/clips/{clip_id}/subtitles")
    assert subs.status_code == 200 and b"-->" in subs.content

    thumbs = client.post("/api/thumbnails/render", json={
        "video_id": vid, "clip_id": clip_id, "headline": "Stop guessing",
        "styles": ["bold_lower", "split_band"]})
    assert thumbs.status_code == 200 and len(thumbs.json()) == 2
    for t in thumbs.json():
        assert isinstance(t["score"]["score"], (int, float))
        img = client.get(f"/api/thumbnails/{t['id']}/image")
        assert img.status_code == 200 and len(img.content) > 5_000

    seo = client.post("/api/content/generate",
                      json={"clip_id": clip_id, "platform": "youtube_shorts"}).json()
    assert len(seo["titles"]) == 3
    assert seo["source"] == "offline"      # no key configured in tests
    assert seo["hashtags"] and seo["description"]

    stored = client.get(f"/api/content?clip_id={clip_id}").json()
    assert len(stored) >= 6

    overview = client.get("/api/analytics/overview").json()
    assert overview["clips"] == 1 and overview["clips_ready"] == 1
    assert "locally generated" in overview["source_note"]


def test_adjusting_timestamps_rerenders_the_same_clip(uploaded_video):
    client, _proj, video = uploaded_video
    vid = video["id"]
    client.post(f"/api/videos/{vid}/analyse", params={"sync": True, "clip_seconds": 4})
    r = client.post("/api/clips", params={"sync": True}, json={
        "video_id": vid, "start_s": 0.0, "end_s": 4.0, "title": "First"})
    clip_id = r.json()["output"]["clips"][0]["clip_id"]

    r = client.patch(f"/api/clips/{clip_id}", params={"sync": True},
                     json={"start_s": 1.0, "end_s": 6.0, "title": "Adjusted"})
    body = r.json()
    assert body["status"] == "succeeded"
    assert body["clip"]["id"] == clip_id          # same row, re-rendered
    assert body["clip"]["title"] == "Adjusted"
    assert body["clip"]["start_s"] == 1.0


def test_invalid_clip_ranges_are_rejected(uploaded_video):
    client, _proj, video = uploaded_video
    vid = video["id"]
    bad = [
        {"start_s": 5, "end_s": 5},        # zero length
        {"start_s": 5, "end_s": 1},        # backwards
        {"start_s": 0, "end_s": 1},        # shorter than the minimum
        {"start_s": 0, "end_s": 999},      # past the end of the video
    ]
    for case in bad:
        r = client.post("/api/clips", params={"sync": True},
                        json={"video_id": vid, "title": "bad", **case})
        assert r.status_code == 422, f"{case} should be rejected, got {r.status_code}"


def test_full_pipeline_runs_all_four_agents(uploaded_video):
    client, _proj, video = uploaded_video
    r = client.post(f"/api/videos/{video['id']}/pipeline",
                    params={"sync": True, "clip_seconds": 4, "count": 1})
    assert r.status_code == 202, r.text
    results = r.json()["results"]
    assert "video_intelligence" in results and results["video_intelligence"]["status"] == "succeeded"
    assert "editing" in results and results["editing"]["status"] == "succeeded"
    assert any(k.startswith("design:") for k in results)
    assert any(k.startswith("seo:") for k in results)
