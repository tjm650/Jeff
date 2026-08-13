"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "motion/react";
import { logo } from "../../assets.js";

const NavigationBar: React.FC = () => {
  const pathname = usePathname();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      const scrollTop = window.scrollY;
      setIsScrolled(scrollTop > 10); // Change background after scrolling 10px
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    if (isScrolled) {
      document.body.classList.add("pt-16");
    } else {
      document.body.classList.remove("pt-16");
    }
  }, [isScrolled]);

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  return (
    <nav
      className={`${
        isScrolled
          ? "fixed top-0 left-0 right-0 z-50 bg-opacity-10  bg-auto border-b-black"
          : "relative z-50"
      } backdrop-blur-xs bg-blur-lg text-gray-900 transition-all duration-700 bg-[#ffffff]/85 md:py-1`}
    >
      {/* Desktop Menu */}
      <div className="max-w-7xl  mx-auto px-4 sm:px-6 lg:px-8 hidden md:block">
        <div className="flex justify-between items-center h-16 ">
          <div className="flex gap-20">
            {/* Logo/Brand */}
            <div className="flex items-center">
              <Link href="/" className="flex items-center space-x-2">
                <img
                  src={logo}
                  alt="Jeff Logo"
                  className="w-10 h-10 rounded-full"
                />
                <span className="font-bold text-xl text-[#1F4788]">Jeff</span>
              </Link>
            </div>

            {/* Navigation Links */}
            <div className="hidden md:flex items-center space-x-8">
              <Link
                href="/"
                className={`${
                  pathname === "/" ? "text-[#1F4788]" : ""
                } hover:text-[#1F4788] transition-colors duration-200`}
              >
                Home
              </Link>
              {/* <Link
                href="/cart"
                className={`${
                  pathname === "/cart" ? "text-[#1F4788]" : ""
                } hover:text-[#1F4788] transition-colors duration-200`}
              >
                Cart
              </Link> */}
              <Link
                href="/privacy"
                className={`${
                  pathname === "/privacy" ? "text-[#1F4788]" : ""
                } hover:text-[#1F4788] transition-colors duration-200`}
              >
                Privacy
              </Link>
              <a
                href={process.env.HELP_CENTER_WA_NUMBER}
                target="_blank"
                rel="noopener noreferrer"
                className={`${
                  pathname === "/help" ? "text-[#1F4788]" : ""
                } hover:text-[#1F4788] transition-colors duration-200`}
              >
                Help Center
              </a>
            </div>
          </div>

          <motion.div
            className="hidden md:block " 
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }} 
          >
            <a
              href={process.env.JEFF_WA_NUMBER}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center border-black border justify-center px-4 py-2 bg-[#25D366] text-black font-medium rounded-4xl hover:bg-[#b1facc] transition-colors duration-200 text-md flex-1 sm:flex-none"
            >
              <svg
                className="w-8 h-8 mr-2 text-white"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893A11.821 11.821 0 0020.885 3.488" />
              </svg>
              Get Started
            </a>
          </motion.div>

          {/* Mobile menu button */}
          {/* <div className="md:hidden absolute top-5 right-5">
            <button
              onClick={toggleMobileMenu}
              className="text-gray-900  cursor-pointer hover:text-[#1F4788] focus:outline-none focus:text-[#1F4788]"
            >
              <svg
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
            </button>
          </div> */}
        </div>
      </div>

      {/* Mobile Menu - Slide from right */}
      <div
        className={`
          md:hidden z-99 top-0 left-0 right-0 h-16 w-full bg-opacity-10   backdrop-blur-xs bg-blur-lg transform transition-transform duration-700 ease-in-out
      `}
      >
        <div className="flex flex-col h-full">
          <div className="flex justify-between p-4">
            {/* Close button */}
            {isMobileMenuOpen ? (
              <button
                onClick={toggleMobileMenu}
                className="text-gray-900 hover:text-[#1F4788] cursor-pointer focus:outline-none"
              >
                <svg
                  className="h-6 w-6"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            ) : (
              <button
                onClick={toggleMobileMenu}
                className="text-gray-900  cursor-pointer hover:text-[#1F4788] focus:outline-none focus:text-[#1F4788]"
              >
                <svg
                  className="h-6 w-6"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                </svg>
              </button>
            )}
            {/* Jeff Logp */}
            <div className="flex items-center">
              <Link href="/" className="flex items-center space-x-2">
                <img
                  src={logo}
                  alt="Jeff Logo"
                  className="w-8 h-8 rounded-full"
                />
                <span className="font-semibold text-lg text-[#1F4788]">
                  Jeff
                </span>
              </Link>
            </div>

            <motion.div
              className="block md:hidden "
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <a
                href="https://wa.me/263771234567"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center border-black border justify-center px-2 py-2 bg-[#25D366] text-black font-medium rounded-4xl hover:bg-[#b1facc] transition-colors duration-200 text-md flex-1 sm:flex-none"
              >
                Start {"  "}
                <svg
                  className="w-5 h-5 ml-2 text-white"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893A11.821 11.821 0 0020.885 3.488" />
                </svg>
              </a>
            </motion.div>
          </div>

          {/* Menu items */}
          <div
            className={`flex-1 px-4 py-4 space-y-10 mb-15 rounded-l-2xl w-full  bg-[#ffffff]  transform transition-transform duration-300 ease-in-out ${
              isMobileMenuOpen ? "translate-x-[50%]" : "translate-x-[500%]"
            } $`}
          >
            <Link
              href="/"
              className={`block ${
                pathname === "/" ? "text-[#1F4788]" : "text-gray-900"
              } hover:text-[#1F4788] transition-colors duration-200 text-lg font-medium`}
              onClick={() => setIsMobileMenuOpen(false)}
            >
              Home
            </Link>
            {/* <Link
              href="/cart"
              className={`block ${
                pathname === "/cart" ? "text-[#1F4788]" : "text-gray-900"
              } hover:text-[#1F4788] transition-colors duration-200 text-lg font-medium`}
              onClick={() => setIsMobileMenuOpen(false)}
            >
              Cart
            </Link> */}
            <Link
              href="/privacy"
              className={`block ${
                pathname === "/privacy" ? "text-[#1F4788]" : "text-gray-900"
              } hover:text-[#1F4788] transition-colors duration-200 text-lg font-medium`}
              onClick={() => setIsMobileMenuOpen(false)}
            >
              Privacy
            </Link>
            <a
              href="https://wa.me/263771234567"
              target="_blank"
              rel="noopener noreferrer"
              className={`${
                  pathname === "/help" ? "text-[#1F4788]" : ""
                } hover:text-[#1F4788] transition-colors duration-200 text-lg font-medium`}
            >
              Help Center
            </a>
          </div>
        </div>
      </div>

      {/* Mobile menu overlay */}
      {isMobileMenuOpen && (
        <div
          className="md:hidden fixed top-1 h-full inset-0 bg-opacity-50 z-99"
          onClick={toggleMobileMenu}
        ></div>
      )}
    </nav>
  );
};

export default NavigationBar;
