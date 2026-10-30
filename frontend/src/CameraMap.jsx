import React, { useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png"
});

const API = "http://127.0.0.1:8000";

const cameras = [
  {
    id: 1,
    name: "Camera 01",
    location: "Pune University Road",
    position: [18.5535, 73.8258],
    status: "ONLINE",
    vehicles: 42,
    traffic: "HIGH",
    videoUrl: `${API}/camera-feeds/camera_01.mp4`
  },
  {
    id: 2,
    name: "Camera 02",
    location: "Shivajinagar Junction",
    position: [18.5308, 73.8475],
    status: "ONLINE",
    vehicles: 28,
    traffic: "MEDIUM",
    videoUrl: `${API}/camera-feeds/camera_02.mp4`
  },
  {
    id: 3,
    name: "Camera 03",
    location: "Swargate Junction",
    position: [18.5018, 73.8636],
    status: "ONLINE",
    vehicles: 61,
    traffic: "HIGH",
    videoUrl: `${API}/camera-feeds/camera_03.mp4`
  },
  {
    id: 4,
    name: "Camera 04",
    location: "Kothrud",
    position: [18.5074, 73.8077],
    status: "OFFLINE",
    vehicles: 0,
    traffic: "UNKNOWN",
    videoUrl: null
  },
  {
    id: 5,
    name: "Camera 05",
    location: "Hinjewadi Phase 1",
    position: [18.5913, 73.7389],
    status: "ONLINE",
    vehicles: 35,
    traffic: "MEDIUM",
    videoUrl: `${API}/camera-feeds/camera_05.mp4`
  }
];

export default function CameraMap() {
  const [selectedCamera, setSelectedCamera] = useState(null);

  const openCamera = (camera) => {
    setSelectedCamera(camera);
  };

  const closeCamera = () => {
    setSelectedCamera(null);
  };

  return (
    <div className="camera-map-panel">

      {/* HEADER */}
      <div className="camera-map-header">

        <div>
          <span className="eyebrow">
            SMART CITY NETWORK
          </span>

          <h3>Traffic Camera Map</h3>

          <p>
            Select a camera location to view traffic intelligence.
          </p>
        </div>

        <div className="camera-map-status">

          <span className="status-dot"></span>

          {cameras.filter(
            (camera) => camera.status === "ONLINE"
          ).length}{" "}
          CAMERAS ONLINE

        </div>

      </div>

      {/* MAP */}
      <div className="camera-map">

        <MapContainer
          center={[18.5204, 73.8567]}
          zoom={12}
          scrollWheelZoom={true}
          style={{
            height: "520px",
            width: "100%"
          }}
        >

          <TileLayer
            attribution="&copy; OpenStreetMap contributors"
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {cameras.map((camera) => (

            <Marker
              key={camera.id}
              position={camera.position}
            >

              <Popup>

                <div className="camera-popup">

                  <strong>
                    {camera.name}
                  </strong>

                  <span>
                    {camera.location}
                  </span>

                  <span>
                    Status:{" "}
                    <b
                      style={{
                        color:
                          camera.status === "ONLINE"
                            ? "green"
                            : "red"
                      }}
                    >
                      {camera.status}
                    </b>
                  </span>

                  <span>
                    Vehicles:{" "}
                    <b>{camera.vehicles}</b>
                  </span>

                  <span>
                    Traffic:{" "}
                    <b>{camera.traffic}</b>
                  </span>

                  <button
                    onClick={() => openCamera(camera)}
                    disabled={
                      camera.status === "OFFLINE"
                    }
                  >
                    {camera.status === "ONLINE"
                      ? "OPEN CAMERA →"
                      : "CAMERA OFFLINE"}
                  </button>

                </div>

              </Popup>

            </Marker>

          ))}

        </MapContainer>

      </div>

      {/* CAMERA MODAL */}
      {selectedCamera && (

        <div
          className="camera-modal-overlay"
          onClick={closeCamera}
        >

          <div
            className="camera-modal"
            onClick={(event) =>
              event.stopPropagation()
            }
          >

            {/* MODAL HEADER */}
            <div className="camera-modal-header">

              <div>

                <span className="eyebrow">
                  LIVE TRAFFIC CAMERA
                </span>

                <h3>
                  {selectedCamera.name}
                </h3>

                <p>
                  {selectedCamera.location}
                </p>

              </div>

              <button
                className="camera-modal-close"
                onClick={closeCamera}
              >
                ✕
              </button>

            </div>

            {/* VIDEO */}
            <div className="camera-feed">

              <div className="camera-feed-overlay">

                <span className="live-indicator">
                  ● LIVE
                </span>

                <span>
                  {selectedCamera.name}
                </span>

              </div>

              {selectedCamera.videoUrl ? (

                <video
                  key={selectedCamera.videoUrl}
                  src={selectedCamera.videoUrl}
                  controls
                  autoPlay
                  muted
                  loop
                  playsInline
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "cover"
                  }}
                />

              ) : (

                <div className="camera-feed-placeholder">

                  <div className="camera-feed-icon">
                    📹
                  </div>

                  <h3>
                    Camera Offline
                  </h3>

                  <p>
                    This camera is currently unavailable.
                  </p>

                </div>

              )}

            </div>

            {/* INFORMATION */}
            <div className="camera-info-grid">

              <div>

                <span>
                  STATUS
                </span>

                <strong
                  className={
                    selectedCamera.status === "ONLINE"
                      ? "camera-online-text"
                      : ""
                  }
                >
                  ● {selectedCamera.status}
                </strong>

              </div>

              <div>

                <span>
                  VEHICLES
                </span>

                <strong>
                  {selectedCamera.vehicles}
                </strong>

              </div>

              <div>

                <span>
                  TRAFFIC
                </span>

                <strong>
                  {selectedCamera.traffic}
                </strong>

              </div>

              <div>

                <span>
                  LOCATION
                </span>

                <strong>
                  {selectedCamera.location}
                </strong>

              </div>

            </div>

            {/* CLOSE */}
            <button
              className="camera-modal-close-action"
              onClick={closeCamera}
            >
              CLOSE CAMERA
            </button>

          </div>

        </div>

      )}

    </div>
  );
}