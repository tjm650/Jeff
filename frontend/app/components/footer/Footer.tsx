"use client";

import React from "react";
import Link from "next/link";
import { logo } from "../../assets.js";

const Footer: React.FC = () => {
  return (
    <footer className="bg-gray-700 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand Section */}
          <div className="hidden md:flex md:flex-col space-y-4 md:space-y-5 *:flex-row *:items-center space-x-10">
            <div className="flex items-center space-x-2">
              <img
                src={logo}
                alt="Jeff Logo"
                className="w-8 h-8 rounded-full"
              />
              <span className="font-semibold text-lg">Jeff</span>
            </div>
            <a
              href={process.env.JEFF_WA_NUMBER}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex cursor-pointer items-center px-4 py-2 bg-[#25D366] text-white font-medium rounded-4xl hover:bg-[#7494c8] transition-colors duration-200 text-sm w-fit"
            >
              <svg
                className="w-4 h-4 mr-2"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893A11.821 11.821 0 0020.885 3.488" />
              </svg>
              Chat
            </a>
            <div className="">
              <Link
                href="/privacy"
                className="text-xs text-gray-300 hover:text-[#7494c8] transition-colors duration-200"
              >
                Terms & Privacy Policy
              </Link>
            </div>
          </div>

          {/* What we do*/}
          <div className="space-y-4">
            <h3 className="text-sm text-gray-400">What we do</h3>
            <div className="space-y-5 gap-y-20  text-lg">
              <Link
                href="/"
                className="block text-gray-300 hover:text-[#7494c8] transition-colors duration-200"
              >
                Accommodation
              </Link>
              <Link
                href="/"
                className="block text-gray-300 hover:text-[#7494c8] transition-colors duration-200"
              >
                Student
              </Link>
              <Link
                href="/"
                className="block text-gray-300 hover:text-[#7494c8] transition-colors duration-200"
              >
                Provider
              </Link>
              <Link
                href="/privacy"
                className="block text-gray-300 hover:text-[#7494c8] transition-colors duration-200"
              ></Link>
            </div>
          </div>

          {/* Quick Links */}
          <div className="space-y-4">
            <h3 className="text-sm text-gray-400">Links</h3>

            <div className="space-y-5 gap-y-20  text-lg">
              <Link
                href="/"
                className="block text-gray-300 hover:text-[#7494c8] transition-colors duration-200"
              >
                Home
              </Link>
              <Link
                href="/cart"
                className="block text-gray-300 hover:text-[#7494c8] transition-colors duration-200"
              >
                Cart
              </Link>
              <Link
                href="/privacy"
                className="block text-gray-300 hover:text-[#7494c8] transition-colors duration-200"
              >
                Privacy
              </Link>
            </div>
          </div>

          {/* Contact Info */}
          <div className="flex flex-col space-y-4 md:space-y-5">
            <div className="space-y-4">
              <h3 className="text-sm text-gray-400">Contact us</h3>

              <div className="space-y-2 text-gray-300 text-sm">
                <p>Jeff Chat</p>
                <p>Customer Service</p>
                <div className="flex sm:flex-row gap-3 mt-4">
                  <a
                    href={process.env.JEFF_WA_NUMBER}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex lg:inline-flex md:hidden items-center cursor-pointer justify-center px-4 py-2 bg-[#25D366] text-white font-medium rounded-4xl hover:bg-[#7494c8] transition-colors duration-200 text-sm flex-1 sm:flex-none"
                  >
                    <svg
                      className="w-4 h-4 mr-2"
                      fill="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893A11.821 11.821 0 0020.885 3.488" />
                    </svg>
                    Jeff
                  </a>
                  <a
                    href={process.env.HELP_CENTER_WA_NUMBER}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center cursor-pointer justify-center px-4 py-2 bg-[#25D366] text-white font-medium rounded-4xl hover:bg-[#7494c8] transition-colors duration-200 text-sm flex-1 sm:flex-none"
                  >
                    <svg
                      className="w-4 h-4 mr-2"
                      fill="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893A11.821 11.821 0 0020.885 3.488" />
                    </svg>
                    Help
                  </a>
                  <a
                    href={"tel:+" + process.env.HELP_CENTER_CALL_NUMBER}
                    // href="tel:+263771234567"
                    className="flex items-center cursor-pointer justify-center w-10 h-10 bg-[#7494c8] text-white rounded-full hover:bg-[#000000] transition-colors duration-200 shrink-0"
                    title="Call us"
                  >
                    <svg
                      className="w-5 h-5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
                      />
                    </svg>
                  </a>
                </div>
              </div>
            </div>
            <p className="hidden text-xs text-gray-400 mt-4 md:block">
              © 2025 Jeff. All rights reserved.
            </p>
          </div>

          {/* Disclaimer */}
          <p className="block text-center justify-self-center text-xs text-gray-400 mt-4 md:hidden">
            © 2025 Jeff. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
