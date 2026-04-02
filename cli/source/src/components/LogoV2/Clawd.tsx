import * as React from 'react';
import { Text } from '../../ink.js';
export type ClawdPose = 'default' | 'arms-up' | 'look-left' | 'look-right';

type Props = {
  pose?: ClawdPose;
};

/**
 * Claw-ED mascot — the apple.
 * Replaces the original Claude crab mascot.
 */
export function Clawd(_props: Props) {
  return <Text>🍎</Text>;
}
