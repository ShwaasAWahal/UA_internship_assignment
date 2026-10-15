import React, { useEffect, useState } from "react";

export interface Announcement {
  id: number;
  message: string;
  type: "success" | "error" | "info";
}

interface LiveAnnouncerProps {
  announcement: Announcement | null;
}

export const LiveAnnouncer: React.FC<LiveAnnouncerProps> = ({ announcement }) => {
  const [visibleToast, setVisibleToast] = useState<Announcement | null>(null);

  useEffect(() => {
    if (announcement) {
      setVisibleToast(announcement);
      const timer = setTimeout(() => {
        setVisibleToast(null);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [announcement]);

  return (
    <>
      {/* Dedicated persistent screen reader live region */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {announcement ? announcement.message : ""}
      </div>

      {/* Visual transient toast for sighted users (hidden from screen readers to prevent duplicate reading) */}
      {visibleToast && (
        <div className="live-region" aria-hidden="true">
          <div className={`live-toast ${visibleToast.type}`}>
            {visibleToast.message}
          </div>
        </div>
      )}
    </>
  );
};
