'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import DOMPurify from 'dompurify';

interface AboutInfo {
  html: string;
}

const PrivacyPage: React.FC = () => {
  const [aboutInfo, setAboutInfo] = useState<AboutInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAboutInfo = async () => {
      try {
        const response = await fetch('/controller/privacyController');
        if (response.ok) {
          const data = await response.json();
          setAboutInfo(data);
        }
      } catch (error) {
        console.error('Failed to fetch about information:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAboutInfo();
  }, []);
  return (
    <div className="min-h-screen  bg-white py-5 px-2">
      <div className="max-w-[95%]">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="p-2"
        >

          {/* Content */}
          <div className="prose prose-green max-w-none leading-relaxed">
            {loading ? (
              <div className="animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
                <div className="h-4 bg-gray-200 rounded w-5/6"></div>
              </div>
            ) : (
              <div
                className="text-gray-700 leading-relaxed"
                dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(aboutInfo?.html || 'Terms & Privacy Policy not available now.') }}
              />
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default PrivacyPage;