"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import Peer from "simple-peer";
import { useSocket } from "./useSocket";

type ConnectionStatus = "disconnected" | "connecting" | "connected";

export function useWebRTC(roomId: string | null) {
  const { emit, on } = useSocket();
  const peerRef = useRef<Peer.Instance | null>(null);
  const [remoteStream, setRemoteStream] = useState<MediaStream | null>(null);
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [isMuted, setIsMuted] = useState(false);
  const [isCameraOff, setIsCameraOff] = useState(false);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const connect = useCallback(async () => {
    if (!roomId) return;
    setStatus("connecting");

    try {
      // Get local video + audio stream (doctor's webcam & mic)
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: { width: { ideal: 640 }, height: { ideal: 480 } },
      });
      setLocalStream(stream);

      // Join the signaling room
      emit("join-room", { roomId, role: "doctor" });

      // Listen for offer from robot
      const offCleanup = on("offer", (data: { signal: Peer.SignalData }) => {
        const peer = new Peer({
          initiator: false,
          trickle: true,
          stream,
        });

        peer.signal(data.signal);

        peer.on("signal", (signal) => {
          emit("answer", { roomId, signal });
        });

        peer.on("stream", (remoteStream) => {
          setRemoteStream(remoteStream);
          setStatus("connected");
        });

        peer.on("close", () => {
          setStatus("disconnected");
          setRemoteStream(null);
        });

        peer.on("error", (err) => {
          console.error("[WebRTC] Peer error:", err);
          setStatus("disconnected");
        });

        peerRef.current = peer;
      });

      // Listen for ICE candidates
      const icCleanup = on("ice-candidate", (data: { candidate: RTCIceCandidateInit }) => {
        peerRef.current?.signal(data as any);
      });

      // Handle peer leaving
      const plCleanup = on("peer-left", () => {
        disconnect();
      });

      // Store cleanups for later
      (peerRef as any)._cleanups = [offCleanup, icCleanup, plCleanup];
    } catch (err) {
      console.error("[WebRTC] Failed to connect:", err);
      setStatus("disconnected");
    }
  }, [roomId, emit, on]);

  const disconnect = useCallback(() => {
    if (peerRef.current) {
      peerRef.current.destroy();
      peerRef.current = null;
    }
    if (localStream) {
      localStream.getTracks().forEach((t) => t.stop());
      setLocalStream(null);
    }
    // Clean up socket listeners
    if ((peerRef as any)._cleanups) {
      (peerRef as any)._cleanups.forEach((fn: () => void) => fn());
    }
    if (roomId) {
      emit("leave-room", { roomId });
    }
    setRemoteStream(null);
    setStatus("disconnected");
    setIsCameraOff(false);
  }, [localStream, roomId, emit]);

  const toggleMute = useCallback(() => {
    if (localStream) {
      const audioTrack = localStream.getAudioTracks()[0];
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled;
        setIsMuted(!audioTrack.enabled);
      }
    }
  }, [localStream]);

  const toggleCamera = useCallback(() => {
    if (localStream) {
      const videoTrack = localStream.getVideoTracks()[0];
      if (videoTrack) {
        videoTrack.enabled = !videoTrack.enabled;
        setIsCameraOff(!videoTrack.enabled);
      }
    }
  }, [localStream]);

  return {
    localStream,
    remoteStream,
    status,
    isMuted,
    isCameraOff,
    connect,
    disconnect,
    toggleMute,
    toggleCamera,
  };
}
