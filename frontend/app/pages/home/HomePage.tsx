"use client";

import React from "react";
import Link from "next/link";
import { motion } from "motion/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faAngleRight } from "@fortawesome/free-solid-svg-icons";
import {
  headerImage,
  jeffHeaderMsgR,
  jeffHeaderMsgS,
  heroPrivacyVideo,
  jeffConfirmMsg,
} from "../../assets.js";

const HomePage: React.FC = () => {
  return (
    <div className="min-h-screen z-1 pt-5 ">
      {/* Header Section */}
      <section
        className="relative mx-10 bg-cover rounded-4xl bg-center bg-no-repeat"
        style={{ backgroundImage: `url(${headerImage})` }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-15">
          <div className="flex flex-col lg:flex-row items-center justify-between">
            <motion.div
              initial={{ opacity: 0, y: -50 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
              className="lg:w-1/2 mb-10 w-[80%] lg:mb-0 text-center lg:text-left"
            >
              <h1 className="text-2xl lg:text-6xl md:text-4xl font-bold text-white mb-6">
                Find Accommodation with Jeff
              </h1>
              <p className="text-lg md:text-xl text-white/90 max-w-md">
                Fast, safe, reliable, 24/7, reccommended listings
              </p>

              <motion.div
                className="gap-20 pt-5 hidden lg:flex md:hidden"
                initial={{ y: 30, opacity: 0 }}
                whileInView={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.6, delay: 1 }}
              >
                <motion.div
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <a
                    href={process.env.JEFF_WA_NUMBER}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center  border-[#e9f9fa] border justify-center px-4 py-2 bg-[#25D366] text-white font-medium rounded-4xl transition-colors duration-200 text-md flex-1 sm:flex-none"
                  >
                    <svg
                      className="w-8 h-8 mr-2"
                      fill="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893A11.821 11.821 0 0020.885 3.488" />
                    </svg>
                    Get Started
                  </a>
                </motion.div>
                <motion.div
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <Link
                    href="/cart"
                    className="inline-flex h-13 items-center border-black border justify-center px-8 py-2 bg-white text-black font-medium rounded-4xl transition-colors duration-200 text-md flex-1 sm:flex-none"
                  >
                    Visit Cart <FontAwesomeIcon icon={faAngleRight} />
                  </Link>
                </motion.div>
              </motion.div>
            </motion.div>

            <div className="lg:w-1/2 flex flex-col items-center lg:items-end space-y-6">
              <motion.div
                initial={{ y: 30, opacity: 0 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.5 }}
              >
                <img
                  src="/jeff-header-msg-r.png"
                  alt="Jeff Header Message R"
                  className="w-90 h-auto drop-shadow-lg"
                />
              </motion.div>
              <motion.div
                initial={{ y: 30, opacity: 0 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 1.4 }}
              >
                <img
                  src={jeffHeaderMsgS}
                  alt="Jeff Header Message S"
                  className="w-120 h-auto drop-shadow-lg"
                />
              </motion.div>
            </div>
          </div>
        </div>
      </section>

      {/* Hero Section */}
      {/* Home Section */}
      <section className="relative mx-10 bg-cover rounded-4xl bg-center bg-no-repeat">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5">
          <div className="flex flex-col lg:flex-row items-center justify-between">
            <motion.div
              initial={{ opacity: 0, y: 50 }}
              whileInView={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.3 }}
              className="lg:w-1/2 mb-10 lg:mb-0 text-center lg:text-left"
            >
              <h2 className="text-2xl max-w-[85%] md:text-2xl lg:text-5xl text-gray-700 font-semibol mb-6">
                Describe specifically what you are looking for
              </h2>
              <p className="text-lg md:text-xl text-gray-700 max-w-md">
                Explore preferable accommodation listings with best ratings from
                the previous students, with respect to your need. Get
                accommodation within short period of time.
              </p>
            </motion.div>

            <div className="lg:w-1/2 py-10 flex text-center flex-col justify-center items-center space-y-2">
              <motion.div
                initial={{ y: 50, opacity: 0 }}
                whileInView={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.6, delay: 0.5 }}
                className="lg:w-150 md:w-150  h-auto drop-shadow-lg *:w-150"
              >
                <img
                  src={jeffConfirmMsg}
                  alt="Jeff Header Message R"
                  className="w-150 h-auto drop-shadow-lg"
                />
              </motion.div>
              {/* <h3 className="text-xl md:pr-20 text-center md:text-xl lg:text-3xl text-gray-700 font-semibol mb-6">
                Confirmation within 8 hours
              </h3> */}
            </div>
          </div>
        </div>
      </section>

      {/* Privacy Section */}
      <section className="relative mx-10 bg-cover rounded-4xl bg-center bg-no-repeat">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5">
          <div className="flex flex-col lg:flex-row-reverse items-center justify-between">
            <motion.div
              initial={{ opacity: 0, y: 50 }}
              whileInView={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.3 }}
              className="lg:w-1/2 mb-10 lg:mb-0 text-center lg:text-left"
            >
              <h2 className="text-2xl max-w-[85%] md:text-2xl lg:text-5xl text-gray-700 font-semibol mb-6">
                Your accommodation search is safe with Jeff
              </h2>
              <p className="text-lg md:text-xl text-gray-700 max-w-md">
                Search through reccommended accommodation listings. Find perfect
                place. Your accommodation is confirmed by the provider. All is
                secured from start to finishing.{"  "}
                <motion.span
                  initial={{ y: 30, opacity: 0 }}
                  whileInView={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.5 }}
                >
                  <Link href="/privacy" className=" text-[#7494c8]">
                    Read Privacy
                  </Link>
                </motion.span>
              </p>
            </motion.div>

            <div className="lg:w-1/2 flex flex-col items-center lg:items-start justify-between space-y-6">
              <motion.div
                initial={{ y: 30, opacity: 0 }}
                whileInView={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.6, delay: 0.5 }}
              >
                <video
                  src={heroPrivacyVideo}
                  className="w-80 h-auto drop-shadow-lg rounded-2xl"
                  autoPlay
                  loop
                  muted
                  playsInline
                />
              </motion.div>
              <motion.div
                initial={{ y: 30, opacity: 0 }}
                whileInView={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.6, delay: 1 }}
              >
                <h3 className="text-xl px-15 text-center md:text-xl lg:text-3xl text-gray-700 font-semibol mb-6">
                  Safe search
                </h3>
              </motion.div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default HomePage;
