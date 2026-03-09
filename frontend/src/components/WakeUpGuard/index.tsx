import React from 'react';

/**
 * WakeUpGuard — passthrough wrapper.
 *
 * Previously pinged the backend /health endpoint to handle cold-start.
 * Now that all data is hardcoded, it simply renders children immediately.
 */
const WakeUpGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <>{children}</>;
};

export default WakeUpGuard;
