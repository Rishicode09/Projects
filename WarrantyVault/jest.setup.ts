/* eslint-disable @typescript-eslint/no-empty-function */
import '@testing-library/react-native/extend-expect';

// Silence Expo notifications native module in the test environment.
jest.mock('expo-notifications', () => ({
  setNotificationHandler: jest.fn(),
  scheduleNotificationAsync: jest.fn(async () => 'notification-id'),
  cancelScheduledNotificationAsync: jest.fn(async () => {}),
  cancelAllScheduledNotificationsAsync: jest.fn(async () => {}),
  getAllScheduledNotificationsAsync: jest.fn(async () => []),
  requestPermissionsAsync: jest.fn(async () => ({ granted: true, status: 'granted' })),
  getPermissionsAsync: jest.fn(async () => ({ granted: true, status: 'granted' })),
  SchedulableTriggerInputTypes: { DATE: 'date' },
}));

jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock')
);
