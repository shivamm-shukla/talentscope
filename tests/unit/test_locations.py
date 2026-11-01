from analysis.locations import canonical_location, location_matches, location_set


def test_city_aliases_share_one_canonical_name() -> None:
    assert canonical_location("Bengaluru") == canonical_location("bangalore ")
    assert canonical_location("Gurugram") == "gurgaon"
    assert canonical_location("Work From Home") == "remote"
    assert canonical_location("Kochi") == "kochi"


def test_multi_city_postings_are_split() -> None:
    assert location_set("Bangalore, Pune / Gurugram") == {
        "bangalore",
        "pune",
        "gurgaon",
    }
    assert location_set("Mumbai and Navi Mumbai") == {"mumbai"}


def test_location_matches_across_aliases_and_lists() -> None:
    assert location_matches(["Bangalore"], "Bengaluru")
    assert location_matches(["pune"], "Bengaluru, Pune")
    assert not location_matches(["Delhi"], "Bengaluru, Pune")


def test_no_desired_location_matches_everything() -> None:
    assert location_matches([], "Anywhere at all")
    assert location_matches(["  "], "Pune")


def test_remote_preference_matches_remote_work_mode() -> None:
    assert location_matches(["Remote"], "Bengaluru", work_mode="remote")
    assert location_matches(["remote"], "Work from home")
    assert not location_matches(["Remote"], "Bengaluru", work_mode="onsite")
