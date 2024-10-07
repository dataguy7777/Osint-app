import streamlit as st
import folium
from sentinelhub import SHConfig, MimeType, CRS, BBox, SentinelHubRequest, DataCollection, bbox_to_dimensions
from streamlit_folium import st_folium
import numpy as np
import logging
from dotenv import load_dotenv
import os
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Configure Logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure Sentinel Hub API using environment variables
config = SHConfig()
config.instance_id = os.getenv("SENTINELHUB_INSTANCE_ID")
config.sh_client_id = os.getenv("SENTINELHUB_CLIENT_ID")
config.sh_client_secret = os.getenv("SENTINELHUB_CLIENT_SECRET")

def validate_sentinelhub_credentials(config):
    """
    Validates the Sentinel Hub API credentials.

    Args:
        config (SHConfig): Sentinel Hub configuration object.

    Raises:
        ValueError: If any of the required credentials are missing.
    """
    if not config.instance_id or not config.sh_client_id or not config.sh_client_secret:
        logger.error("Sentinel Hub API credentials are not properly set in the .env file.")
        raise ValueError("Missing Sentinel Hub API credentials.")

def get_sentinel_image(bbox_coords, date, data_collection=DataCollection.SENTINEL2_L1C):
    """
    Fetches a satellite image from Sentinel Hub based on the provided bounding box and date.

    Args:
        bbox_coords (list): Bounding box coordinates [min_lon, min_lat, max_lon, max_lat].
        date (str): Date in ISO format (YYYY-MM-DD).
        data_collection (DataCollection, optional): Sentinel data collection. Defaults to SENTINEL2_L1C.

    Returns:
        bytes: Image data in PNG format.
    """
    try:
        logger.info(f"Fetching satellite image for date: {date} and bbox: {bbox_coords}")
        bbox = BBox(bbox_coords, crs=CRS.WGS84)
        resolution = 10  # meters per pixel

        # Calculate dimensions based on bounding box and resolution
        size = bbox_to_dimensions(bbox, resolution=resolution)

        # Create Sentinel Hub request
        request = SentinelHubRequest(
            data_collection=data_collection,
            input_data=[
                SentinelHubRequest.input_data(
                    time_interval=(date, date)
                )
            ],
            responses=[
                SentinelHubRequest.output_response('default', MimeType.PNG)
            ],
            bbox=bbox,
            size=size,
            config=config
        )

        # Execute the request and retrieve the image
        response = request.get_data()
        logger.info("Satellite image fetched successfully.")
        return response[0]

    except Exception as e:
        logger.exception("An error occurred while fetching the satellite image.")
        st.error(f"Error fetching image: {e}")
        return None

def initialize_folium_map(lat, lon, zoom):
    """
    Initializes a Folium map centered at the specified latitude and longitude.

    Args:
        lat (float): Latitude for the map center.
        lon (float): Longitude for the map center.
        zoom (int): Initial zoom level.

    Returns:
        folium.Map: Configured Folium map object.
    """
    logger.debug(f"Initializing Folium map at latitude: {lat}, longitude: {lon}, zoom: {zoom}")
    m = folium.Map(location=[lat, lon], zoom_start=zoom)
    folium.Marker([lat, lon], popup="Area of Interest").add_to(m)
    return m

def main():
    """
    Main function to run the Streamlit app.
    """
    # Validate API credentials
    try:
        validate_sentinelhub_credentials(config)
    except ValueError as ve:
        st.error(str(ve))
        st.stop()

    # App Title
    st.title("🌍 Real-Time Satellite Image Processing")

    # Sidebar Configuration
    st.sidebar.header("Configuration")

    # Satellite Selection
    satellite_option = st.sidebar.selectbox(
        "Choose Satellite Data",
        ["Sentinel-2", "Sentinel-3", "Landsat-8"],
        index=0
    )

    # Mapping Satellite Option to DataCollection
    satellite_mapping = {
        "Sentinel-2": DataCollection.SENTINEL2_L1C,
        "Sentinel-3": DataCollection.SENTINEL3_L1,
        "Landsat-8": DataCollection.LANDSAT8_L1
    }
    selected_data_collection = satellite_mapping.get(satellite_option, DataCollection.SENTINEL2_L1C)

    # Area of Interest (AOI) Configuration
    st.sidebar.subheader("Define Area of Interest (AOI)")
    lat = st.sidebar.number_input("Latitude", value=46.1512, format="%.6f")
    lon = st.sidebar.number_input("Longitude", value=14.9955, format="%.6f")
    zoom = st.sidebar.slider("Zoom Level", 1, 15, 10)

    # Initialize and Display Folium Map
    folium_map = initialize_folium_map(lat, lon, zoom)
    st_data = st_folium(folium_map, width=700, height=500)

    # Define Bounding Box based on AOI
    bbox_offset = 0.05  # Degrees offset for bounding box
    bbox_coords = [
        lon - bbox_offset,
        lat - bbox_offset,
        lon + bbox_offset,
        lat + bbox_offset
    ]
    logger.debug(f"Bounding Box Coordinates: {bbox_coords}")

    # Date Selection
    st.sidebar.subheader("Date Selection")
    today = datetime.today().date()
    date = st.sidebar.date_input("Select Date", value=today)

    # Button to Fetch Satellite Image
    if st.sidebar.button("Get Satellite Image"):
        # Validate date input
        if date > today:
            st.error("Selected date cannot be in the future.")
        else:
            # Fetch and Display Satellite Image
            with st.spinner("Fetching satellite image..."):
                image_data = get_sentinel_image(bbox_coords, date.isoformat(), selected_data_collection)
                if image_data is not None:
                    st.success("Satellite image fetched successfully!")
                    st.image(image_data, caption=f"Satellite Image on {date}", use_column_width=True)
                else:
                    st.error("Failed to retrieve satellite image.")

if __name__ == "__main__":
    main()