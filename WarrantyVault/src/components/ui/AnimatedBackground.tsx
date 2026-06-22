import { LinearGradient } from 'expo-linear-gradient';
import { useEffect } from 'react';
import { StyleSheet, useWindowDimensions } from 'react-native';
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';

interface OrbConfig {
  color: string;
  size: number;
  x: number;
  y: number;
  amplitude: number;
  duration: number;
  delay: number;
}

/**
 * A single softly-glowing blob that drifts and pulses forever. Driven by a
 * shared value looping 0 -> 1 (auto-reversing) on the UI thread, so the motion
 * stays smooth without re-rendering React.
 */
function Orb({ color, size, x, y, amplitude, duration, delay }: OrbConfig) {
  const t = useSharedValue(0);

  useEffect(() => {
    t.value = withDelay(
      delay,
      withRepeat(withTiming(1, { duration, easing: Easing.inOut(Easing.quad) }), -1, true)
    );
  }, [t, duration, delay]);

  const style = useAnimatedStyle(() => {
    const offset = (t.value - 0.5) * amplitude;
    return {
      transform: [
        { translateX: x + offset },
        { translateY: y - offset },
        { scale: 0.85 + t.value * 0.35 },
      ],
      opacity: 0.35 + t.value * 0.3,
    };
  });

  return (
    <Animated.View
      pointerEvents="none"
      style={[
        {
          position: 'absolute',
          width: size,
          height: size,
          borderRadius: size / 2,
          backgroundColor: color,
        },
        style,
      ]}
    />
  );
}

/**
 * Full-screen vibrant animated backdrop: a deep gradient base overlaid with
 * several drifting colored orbs and a subtle darkening veil so foreground
 * content stays readable.
 */
export function AnimatedBackground() {
  const { width, height } = useWindowDimensions();

  const orbs: OrbConfig[] = [
    { color: '#6366F1', size: width * 0.9, x: -width * 0.3, y: -height * 0.05, amplitude: 60, duration: 6000, delay: 0 },
    { color: '#A855F7', size: width * 0.8, x: width * 0.5, y: height * 0.12, amplitude: 80, duration: 7000, delay: 400 },
    { color: '#22D3EE', size: width * 0.7, x: width * 0.45, y: height * 0.62, amplitude: 70, duration: 8000, delay: 800 },
    { color: '#EC4899', size: width * 0.75, x: -width * 0.25, y: height * 0.68, amplitude: 90, duration: 6500, delay: 200 },
  ];

  return (
    <Animated.View pointerEvents="none" style={StyleSheet.absoluteFill}>
      <LinearGradient
        colors={['#0B1026', '#0F172A', '#1E1B4B']}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={StyleSheet.absoluteFill}
      />
      {orbs.map((orb, i) => (
        <Orb key={i} {...orb} />
      ))}
      {/* Veil to mute the orbs and guarantee text contrast. */}
      <Animated.View
        style={[StyleSheet.absoluteFill, { backgroundColor: 'rgba(7,10,25,0.35)' }]}
      />
    </Animated.View>
  );
}
