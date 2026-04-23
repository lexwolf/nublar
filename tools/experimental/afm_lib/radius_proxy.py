from __future__ import annotations


RADIUS_PROXY_CHOICES = (
    "equivalent_radius_nm",
    "volume_equivalent_radius_nm",
    "height_equivalent_radius_mean_nm",
    "height_equivalent_radius_p95_nm",
)


SUMMARY_FIELD_FOR_RADIUS_PROXY = {
    "equivalent_radius_nm": "mean_equivalent_radius_nm",
    "volume_equivalent_radius_nm": "mean_volume_equivalent_radius_nm",
    "height_equivalent_radius_mean_nm": "mean_height_equivalent_radius_nm",
    "height_equivalent_radius_p95_nm": "mean_p95_height_equivalent_radius_nm",
}


MANIFEST_RAVE_FIELD_FOR_RADIUS_PROXY = {
    "equivalent_radius_nm": "Rave_equivalent_radius_nm",
    "volume_equivalent_radius_nm": "Rave_volume_equivalent_radius_nm",
    "height_equivalent_radius_mean_nm": "Rave_height_equivalent_radius_mean_nm",
    "height_equivalent_radius_p95_nm": "Rave_height_equivalent_radius_p95_nm",
}
