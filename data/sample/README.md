# Visual Crossing sample response

`visual_crossing_sample.json` is a complete saved Visual Crossing Timeline API
response for **Marquette, Kansas, on October 1, 2026**. It was copied unchanged
from the local raw download for this milestone; it is not synthetic data.

- Requested location: latitude 38.5529, longitude -97.8339.
- Timezone: `America/Chicago`.
- Units: `unitGroup=us` (degrees Fahrenheit, miles per hour, and inches).
- Structure: location metadata, one object in `days`, 24 nested hourly weather
  records, and four related station-metadata objects.
- Historical hourly records are labeled `source=obs`; this is not a forecast.
- Hourly `stations` identifiers link to entries in the top-level `stations` object.
- Daily astronomy values belong to the day, not to each hourly record.

The sample is 10,605 bytes. The saved API key was checked and is absent; no
request URL or authentication parameters were added to the file.

Full downloads stay in `data/raw/visual_crossing/`, which Git ignores. See
[`docs/data_dictionary.md`](../../docs/data_dictionary.md) for field meanings,
missing-value behavior, identifiers, and relationships.

[Weather Data Provided by Visual Crossing](https://www.visualcrossing.com/).
[Timeline API documentation](https://www.visualcrossing.com/resources/documentation/weather-api/timeline-weather-api/).
