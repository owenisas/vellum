import { useDetect } from "../api/chat";

export function useWatermark() {
  const detect = useDetect();
  return {
    detect: (text: string) => detect.mutateAsync(text),
    isDetecting: detect.isPending,
    result: detect.data,
  };
}
