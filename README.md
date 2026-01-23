# K-City | K-Drama Streaming Hub

## Overview
K-City is a web-based streaming application dedicated to Korean Dramas. It utilizes the TMDB API to fetch metadata (posters, ratings, descriptions) and organizes content into a user-friendly, Netflix-style interface.

## Tech Stack
* **Backend:** Python 3, Flask
* **Frontend:** HTML5, TailwindCSS, JavaScript
* **Data Source:** The Movie Database (TMDB) API
* **Server:** Gunicorn

## Features
* **Auto-Sync:** Background threads automatically fetch new trending dramas every 30 minutes.
* **Smart Caching:** Reduces API calls by storing data in a local JSON cache.
* **Pre-Roll Ad System:** Integrated ad-supported playback logic.
* **Responsive Design:** Optimized for mobile viewing.

## Disclaimer
This product uses the TMDB API but is not endorsed or certified by TMDB. This application is for educational purposes.
