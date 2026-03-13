"use client";

import VideoStream from "./VideoStream";
import CallControls from "./CallControls";
import { useWebRTC } from "@/hooks/useWebRTC";

interface VideoPanelProps {
  patientId?: string;
}

export default function VideoPanel({ patientId }: VideoPanelProps) {
  const roomId = patientId ? `patient-${patientId}` : null;
  const {
    localStream,
    remoteStream,
    status,
    isMuted,
    isCameraOff,
    connect,
    disconnect,
    toggleMute,
    toggleCamera,
  } = useWebRTC(roomId);

  return (
    <div className="flex flex-col h-full gap-3">
      {/* Two video feeds side by side */}
      <div className="flex-1 min-h-0 flex gap-2">
        <VideoStream stream={localStream} label="Doctor (You)" muted />
        <VideoStream stream={remoteStream} label="Patient (Robot)" />
      </div>
      <CallControls
        status={status}
        isMuted={isMuted}
        isCameraOff={isCameraOff}
        onConnect={connect}
        onDisconnect={disconnect}
        onToggleMute={toggleMute}
        onToggleCamera={toggleCamera}
      />
    </div>
  );
}
