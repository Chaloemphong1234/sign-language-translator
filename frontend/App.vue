<template>
  <div id="app">
    <header class="navbar">
      <div class="navbar-container">
        <a href="#" class="navbar-brand">🅸🅣 ระบบแปลภาษามือ (พร้อมเสียงอ่าน)</a>
      </div>
    </header>

    <div class="container">
      <section class="camera-section">
        <h1 class="main-title">🖐️มาเริ่มแปลภาษากัน</h1>
        <div class="video-container">
          <video ref="video" autoplay playsinline :class="{'video-box': true, 'active-camera': cameraOn}"></video>
          <div v-if="!cameraOn" class="camera-placeholder">
            <span class="icon">📸</span>
            <p>กรุณาเปิดกล้องเพื่อเริ่มใช้งาน</p>
          </div>
        </div>

        <div class="buttons">
          <button @click="toggleTranslate" :class="['btn', isTranslating ? 'btn-red' : 'btn-blue']">
            {{ isTranslating ? 'หยุดแปล' : 'เริ่มแปล' }}
            <span class="icon">{{ isTranslating ? '⏸️' : '▶️' }}</span>
          </button>
          <button @click="toggleCamera" :class="['btn', cameraOn ? 'btn-gray' : 'btn-green']">
            {{ cameraOn ? 'ปิดกล้อง' : 'เปิดกล้อง' }}
            <span class="icon">{{ cameraOn ? '✖️' : '✔️' }}</span>
          </button>
        </div>

        <div class="status-box">
          <div v-if="loading" class="loading">
            <div class="spinner"></div>
            กำลังแปล...
          </div>
          <div v-if="prediction && !loading" class="result-box animated fadeIn">
            <p class="result-label">ผลการแปล:</p>
            <p class="result-text">{{ prediction }}</p>
          </div>
          <div v-if="errorMsg" class="error-box">
            <p class="error-msg">{{ errorMsg }}</p>
          </div>
        </div>
      </section>

      <section class="history-section">
        <div class="section-header">
          <h2><span class="icon">📜</span> ประวัติการแปลล่าสุด</h2>
        </div>
        <div class="table-wrapper">
          <table class="styled-table">
            <thead>
              <tr>
                <th>ลำดับ</th>
                <th>📷 ภาพ</th>
                <th>📝 คำแปล</th>
                <th>⏰ เวลา</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="translations.length === 0">
                <td colspan="4" class="no-data-row">ไม่มีข้อมูลการแปลในขณะนี้</td>
              </tr>
              <tr v-for="(item, index) in translations" :key="item.id" class="history-row">
                <td>{{ index + 1 }}</td>
                <td>
                  <img :src="`http://localhost:5000/${item.image_path}`" alt="translation" class="thumb" />
                </td>
                <td class="predicted-text">{{ item.predicted_text }}</td>
                <td>{{ formatDate(item.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import mqtt from "mqtt/dist/mqtt"; // สำหรับ browser

export default {
  name: "App",
  data() {
    return {
      loading: false,
      prediction: "",
      errorMsg: "",
      intervalId: null,
      isTranslating: false,
      cameraOn: false,
      stream: null,
      translations: [],
      saving: false,
      mqttClient: null,
    };
  },
  mounted() {
    this.startCamera();
    this.loadTranslations();
    this.connectMQTT();
  },
  beforeDestroy() {
    this.stopTranslation();
    this.stopCamera();
    if (this.mqttClient) this.mqttClient.end();
  },
  methods: {
    // ================= MQTT =================
    connectMQTT() {
      this.mqttClient = mqtt.connect("wss://broker.hivemq.com:8884/mqtt");

      this.mqttClient.on("connect", () => {
        console.log("✅ MQTT connected (Vue)");
        this.mqttClient.subscribe("hand_sign/translation", (err) => {
          if (!err) console.log("📡 Subscribed to hand_sign/translation");
        });
      });

      this.mqttClient.on("message", (topic, message) => {
        console.log("📩 MQTT message:", topic, message.toString());
        if (topic === "hand_sign/translation") {
          this.prediction = message.toString();
          this.speakText(this.prediction);
        }
      });

      this.mqttClient.on("error", (err) => {
        console.error("❌ MQTT error:", err);
      });
    },

    // ================= CAMERA =================
    async startCamera() {
      try {
        this.stream = await navigator.mediaDevices.getUserMedia({ video: true });
        this.$refs.video.srcObject = this.stream;
        this.cameraOn = true;
      } catch (err) {
        this.errorMsg = "ไม่สามารถเข้าถึงกล้องได้ กรุณาอนุญาตการเข้าถึงกล้อง";
        this.cameraOn = false;
      }
    },
    stopCamera() {
      if (this.stream) {
        this.stream.getTracks().forEach(track => track.stop());
        this.stream = null;
      }
      if (this.$refs.video) this.$refs.video.srcObject = null;
      this.cameraOn = false;
    },
    toggleCamera() {
      if (this.cameraOn) {
        this.stopCamera();
        this.stopTranslation();
      } else {
        this.startCamera();
      }
    },

    // ================= TRANSLATION =================
    toggleTranslate() {
      if (this.isTranslating) {
        this.stopTranslation();
      } else {
        if (!this.cameraOn) {
          this.errorMsg = "กรุณาเปิดกล้องก่อนเริ่มแปล";
          return;
        }
        this.startTranslation();
      }
    },
    startTranslation() {
      if (this.intervalId) return;
      this.isTranslating = true;
      this.prediction = "";
      this.errorMsg = "";
      this.intervalId = setInterval(this.sendFrame, 7500);
    },
    stopTranslation() {
      if (this.intervalId) {
        clearInterval(this.intervalId);
        this.intervalId = null;
      }
      this.isTranslating = false;
      this.loading = false;
    },
    async sendFrame() {
      if (this.loading || this.saving) return;
      this.loading = true;
      this.errorMsg = "";

      const video = this.$refs.video;
      if (!video || video.readyState !== 4) {
        this.errorMsg = "กล้องยังไม่พร้อมใช้งาน";
        this.loading = false;
        return;
      }

      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      canvas.toBlob(async (blob) => {
        if (!blob) {
          this.errorMsg = "ไม่สามารถจับภาพได้";
          this.loading = false;
          return;
        }

        try {
          const formData = new FormData();
          formData.append("file", blob, "frame.jpg");

          const response = await axios.post(
            "http://localhost:5001/predict",
            formData,
            { headers: { "Content-Type": "multipart/form-data" } }
          );

          this.prediction = response.data.prediction || "ไม่พบผลลัพธ์";

          if (this.prediction && this.prediction !== "ไม่พบผลลัพธ์") {
            this.speakText(this.prediction);

            // ✅ ส่งผลลัพธ์ไป MQTT
            if (this.mqttClient && this.mqttClient.connected) {
              this.mqttClient.publish("hand_sign/translation", this.prediction);
            }

            // บันทึกลงฐานข้อมูล (ไม่ส่ง gesture แล้ว)
            await this.saveTranslation(blob, this.prediction);
            await this.loadTranslations();
          }
        } catch (error) {
          console.error("เกิดข้อผิดพลาดในการแปล:", error);
          this.errorMsg = "เกิดข้อผิดพลาดในการเชื่อมต่อเซิร์ฟเวอร์แปลภาษามือ";
        }

        this.loading = false;
      }, "image/jpeg");
    },

    async saveTranslation(imageBlob, predictedText) {
      if (this.saving) return;
      this.saving = true;
      const formData = new FormData();
      formData.append("file", imageBlob);
      formData.append("predicted_text", predictedText);

      try {
        await axios.post("http://localhost:5000/server", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      } catch (error) {
        console.error("เกิดข้อผิดพลาดขณะบันทึก:", error);
      }
      this.saving = false;
    },

    // ================= UTILS =================
    speakText(text) {
      if (!window.speechSynthesis) return;
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "th-TH";
      utterance.volume = 1;
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utterance);
    },

    async loadTranslations() {
      try {
        const res = await axios.get("http://localhost:5000/server");
        this.translations = res.data.rows;
      } catch (err) {
        console.error("โหลดข้อมูลล้มเหลว", err);
      }
    },

    formatDate(dateStr) {
  const date = new Date(dateStr);
  // ปรับ timezone เป็น UTC+7
  date.setHours(date.getHours() + 7);
  return date.toLocaleString("th-TH");
    },
  }
};
</script>









<style>
:root {
  --primary-color: #4f46e5;
  --secondary-color: #10b981;
  --danger-color: #ef4444;
  --gray-color: #6b7280;
  --light-gray: #f9fafb;
  --dark-gray: #111827;
  --font-family: 'Sarabun', 'Noto Sans Thai', Arial, sans-serif;
  --border-radius: 16px;
  --box-shadow: 0 10px 25px rgba(0,0,0,0.12);
  --transition: 0.3s ease-in-out;
}

/* ==============================
   BASE
============================== */
body {
  margin: 0;
  font-family: var(--font-family);
  background: linear-gradient(135deg, #e0e7ff, #f9fafb);
  color: var(--dark-gray);
  line-height: 1.6;
}

/* ==============================
   NAVBAR
============================== */
.navbar {
  background: rgba(255,255,255,0.8);
  backdrop-filter: blur(12px);
  box-shadow: 0 4px 15px rgba(0,0,0,0.1);
  padding: 1rem 2rem;
  position: sticky;
  top: 0;
  z-index: 1000;
}

.navbar-container {
  max-width: 1200px;
  margin: auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.navbar-brand {
  font-size: 1.8rem;
  font-weight: 800;
  color: var(--primary-color);
  text-decoration: none;
  letter-spacing: 1px;
}

/* ==============================
   CONTAINER
============================== */
.container {
  max-width: 1200px;
  margin: 2rem auto;
  padding: 0 1rem;
}

/* ==============================
   CAMERA SECTION
============================== */
.camera-section {
  background: rgba(255,255,255,0.75);
  backdrop-filter: blur(15px);
  border-radius: var(--border-radius);
  box-shadow: var(--box-shadow);
  text-align: center;
  padding: 2rem;
  transition: transform var(--transition), box-shadow var(--transition);
}
.camera-section:hover {
  transform: translateY(-6px);
  box-shadow: 0 18px 35px rgba(0,0,0,0.2);
}

.main-title {
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--primary-color);
  margin-bottom: 2rem;
  text-shadow: 0 2px 10px rgba(0,0,0,0.15);
}

.video-container {
  position: relative;
  width: 100%;
  max-width: 640px;
  margin: auto;
  aspect-ratio: 4/3;
  border-radius: var(--border-radius);
  overflow: hidden;
  background: linear-gradient(145deg, #ffffff, #e0e7ff);
  box-shadow: 8px 8px 20px rgba(0,0,0,0.08), -8px -8px 20px rgba(255,255,255,0.8);
}
.video-box {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: none;
}
.video-box.active-camera {
  display: block;
  animation: fadeIn 0.6s ease-in-out;
}
.camera-placeholder {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: var(--gray-color);
  text-align: center;
}
.camera-placeholder .icon {
  font-size: 5rem;
  display: block;
  animation: pulse 1.5s infinite;
}

/* ==============================
   BUTTONS
============================== */
.buttons {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 1rem;
  margin: 2rem 0;
}
.btn {
  padding: 12px 32px;
  font-size: 1.1rem;
  font-weight: 700;
  border-radius: 50px;
  color: white;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all var(--transition);
  box-shadow: 4px 4px 12px rgba(0,0,0,0.15), -4px -4px 12px rgba(255,255,255,0.5);
}
.btn:hover {
  transform: scale(1.06);
  box-shadow: 6px 6px 20px rgba(0,0,0,0.2), -6px -6px 20px rgba(255,255,255,0.6);
}
.btn-blue { background: linear-gradient(135deg,#4f46e5,#818cf8); }
.btn-green { background: linear-gradient(135deg,#10b981,#34d399); }
.btn-red { background: linear-gradient(135deg,#ef4444,#f87171); }
.btn-gray { background: linear-gradient(135deg,#6b7280,#9ca3af); }

/* ==============================
   STATUS BOX
============================== */
.status-box { min-height: 80px; font-size: 1.2rem; }
.loading {
  display: flex; justify-content: center; align-items: center; gap: 12px;
  font-weight: 700; color: var(--primary-color);
}
.spinner {
  border: 4px solid rgba(0,0,0,0.1);
  width: 32px; height: 32px; border-radius: 50%;
  border-left-color: var(--primary-color);
  animation: spin 1s linear infinite;
}
.result-box {
  margin-top: 1rem;
  padding: 1rem 2rem;
  background: rgba(255,255,255,0.6);
  backdrop-filter: blur(10px);
  border-radius: var(--border-radius);
  border-left: 6px solid var(--primary-color);
  font-weight: 600;
  box-shadow: var(--box-shadow);
  animation: fadeIn 0.6s ease-in-out;
}
.error-box {
  margin-top: 1rem;
  background: rgba(255,235,235,0.7);
  border-left: 6px solid var(--danger-color);
  border-radius: var(--border-radius);
  padding: 1rem 1.5rem;
  font-weight: 600;
  color: var(--danger-color);
}

/* ==============================
   HISTORY
============================== */
.history-section {
  margin-top: 2rem;
  background: rgba(255,255,255,0.8);
  backdrop-filter: blur(12px);
  border-radius: var(--border-radius);
  box-shadow: var(--box-shadow);
  padding: 2rem;
}
.section-header h2 {
  font-size: 2rem;
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--primary-color);
  margin-bottom: 1rem;
}
.styled-table {
  width: 100%;
  border-collapse: collapse;
  overflow: hidden;
  border-radius: var(--border-radius);
}
.styled-table thead {
  background: linear-gradient(135deg, var(--primary-color), #6366f1);
  color: white;
}
.styled-table th, .styled-table td {
  padding: 14px;
  text-align: center;
}
.styled-table tbody tr:nth-child(even) {
  background: #f3f4f6;
}
.styled-table tbody tr:hover {
  background: #e0e7ff;
  transition: background 0.3s ease;
}
.thumb {
  width: 90px;
  height: 65px;
  border-radius: var(--border-radius);
  object-fit: cover;
  border: 1px solid #ddd;
}
.predicted-text {
  font-weight: 700;
  color: var(--primary-color);
}

/* ==============================
   ANIMATIONS
============================== */
@keyframes spin { to { transform: rotate(360deg);} }
@keyframes fadeIn { from {opacity:0; transform: translateY(8px);} to {opacity:1; transform: translateY(0);} }
@keyframes pulse { 0%,100% {transform: scale(1); opacity:0.7;} 50%{transform:scale(1.1); opacity:1;} }

/* ==============================
   RESPONSIVE
============================== */
@media (max-width: 768px) {
  .main-title { font-size: 2rem; }
  .buttons { flex-direction: column; }
  .styled-table thead { display: none; }
  .styled-table, .styled-table tbody, .styled-table tr, .styled-table td {
    display: block;
    width: 100%;
  }
  .styled-table tr { margin-bottom: 1rem; background: rgba(255,255,255,0.9); border-radius: var(--border-radius); padding: 1rem; }
  .styled-table td {
    padding: 0.5rem 0;
    text-align: left;
  }
  .thumb { width: 100%; height: auto; }
}

</style>