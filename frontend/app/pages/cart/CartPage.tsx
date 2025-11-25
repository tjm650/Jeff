"use client";

import type { Metadata } from "next";
import { motion } from "motion/react";
import { useState, useEffect } from "react";
import DOMPurify from 'dompurify';

interface PaymentForm {
  chatNumber: string;
  paymentNumber: string;
}

interface CartInfo {
  html: string;
}

const CartPage: React.FC = () => {
  const [formData, setFormData] = useState<PaymentForm>({
    chatNumber: "",
    paymentNumber: "",
  });
  const [cartInfo, setCartInfo] = useState<CartInfo | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [cartLoading, setCartLoading] = useState(true);

  useEffect(() => {
    const fetchCartInfo = async () => {
      try {
        const response = await fetch('/controller/cartController');
        if (response.ok) {
          const data = await response.json();
          setCartInfo(data);
        }
      } catch (error) {
        console.error('Failed to fetch cart information:', error);
      } finally {
        setCartLoading(false);
      }
    };

    fetchCartInfo();
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    // Only allow numbers and limit to 9 digits
    const numericValue = value.replace(/\D/g, "").slice(0, 9);
    setFormData((prev) => ({
      ...prev,
      [name]: numericValue,
    }));
    setError("");
  };

  const validateForm = (): boolean => {
    if (!formData.chatNumber.trim()) {
      setError("Whatsapp Number is required");
      return false;
    }
    if (!formData.paymentNumber.trim()) {
      setError("Payment Number is required");
      return false;
    }

    // Basic phone number validation (Zimbabwe format) - check local part only
    const localPhoneRegex = /^[7-8][0-9]{8}$/;
    if (!localPhoneRegex.test(formData.chatNumber.trim())) {
      setError("Please enter a valid phone number for Chat Number");
      return false;
    }
    if (!localPhoneRegex.test(formData.paymentNumber.trim())) {
      setError("Please enter a valid phone number for Payment Number");
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      // Call PayNow API
      const response = await fetch("/controller/initiate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          whatsapp_number: `+263${formData.chatNumber.trim()}`,
          payment_number: `+263${formData.paymentNumber.trim()}`,
        }),
      });

      const data = await response.json();

      if (data.success) {
        setSuccess(true);
        // Here you would typically redirect to payment status page or show payment instructions
      } else {
        setError(data.message || "Payment initiation failed");
      }
    } catch (err) {
      setError("Network error. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen bg-cover  bg-center bg-no-repeat py-5 px-4"
      style={{ backgroundImage: "url(/jeffimg1.png)" }}
    >
      <div className="max-w-[95%] mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-2 lg:space-x-30 gap-8 items-start">
          {/* Payment Form */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="bg-white rounded-lg justify-self-center  shadow-lg p-8 w-[90%] md:w-[70%] md:justify-self-center"
          >
            {/* Header */}
            <div className="text-center">
              <img
                src="/ecocash.png"
                alt="EcoCash"
                className="h-15 mx-auto mb-2"
              />
            </div>

            {/* Payment Form */}
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Chat Number */}
              <div>
                <label
                  htmlFor="chatNumber"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  WhatsApp
                </label>
                <div className="relative">
                  <span className="absolute left-0 top-0 h-full flex items-center px-3 bg-gray-100 text-gray-600 font-medium border-r border-gray-300 rounded-l-lg">
                    +263
                  </span>
                  <input
                    type="tel"
                    id="chatNumber"
                    name="chatNumber"
                    value={formData.chatNumber}
                    onChange={handleInputChange}
                    placeholder="771234567"
                    pattern="[7-8][0-9]{8}"
                    maxLength={9}
                    inputMode="tel"
                    className="w-full pl-20 pr-4 py-3 border border-gray-300 text-black rounded-lg focus:ring-2 focus:ring-[#1F4788] focus:border-transparent transition-colors duration-200"
                    disabled={isLoading}
                  />
                </div>
              </div>

              {/* Payment Number */}
              <div>
                <label
                  htmlFor="paymentNumber"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Payment
                </label>
                <div className="relative">
                  <span className="absolute left-0 top-0 h-full flex items-center px-3 bg-gray-100 text-gray-600 font-medium border-r border-gray-300 rounded-l-lg">
                    +263
                  </span>
                  <input
                    type="tel"
                    id="paymentNumber"
                    name="paymentNumber"
                    value={formData.paymentNumber}
                    onChange={handleInputChange}
                    placeholder="771234567"
                    pattern="[7-8][0-9]{8}"
                    maxLength={9}
                    inputMode="numeric"
                    className="w-full pl-20 text-black pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1F4788] focus:border-transparent transition-colors duration-200"
                    disabled={isLoading}
                  />
                </div>
              </div>

              {/* Info Section */}
              <div className="mt-8 p-4 text-sm bg-[#F0F0F0] space-y-1 space-x-2 flex items-center rounded-lg">
                {/* <h3 className="text-[#1F4788] ">Price</h3> */}
                <ul className="flex space-x-10 text-[#1F4788] space-y-1">
                  <li>USD:{process.env.NEXT_PUBLIC_TOKEN_PRICE_USD}</li>
                  <li>ZWG:{process.env.NEXT_PUBLIC_TOKEN_PRICE_ZWG}</li>
                </ul>
              </div>

              {/* Error Message */}
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-red-50 border border-red-200 rounded-lg p-4"
                >
                  <div className="flex items-center">
                    <p className="text-red-700 text-sm">{error}</p>
                  </div>
                </motion.div>
              )}

              {/* Submit Button */}
              <motion.button
                whileHover={{ scale: isLoading ? 1 : 1.02 }}
                whileTap={{ scale: isLoading ? 1 : 0.98 }}
                type="submit"
                disabled={isLoading}
                className={`w-full py-3 px-4 rounded-lg font-semibold transition-colors duration-200 ${
                  isLoading
                    ? "bg-[#7494c8] cursor-progress"
                    : "bg-[#1F4788] cursor-pointer hover:bg-[#7494c8] text-white"
                }`}
              >
                {isLoading ? (
                  <div className="flex text-gray-100 items-center justify-center">
                    <div className="relative">
                      <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent mr-2"></div>
                      <div className="absolute inset-0 rounded-full h-5 w-5 border-2 border-white/30 animate-ping"></div>
                    </div>
                    Processing
                  </div>
                ) : (
                  "Purchase"
                )}
              </motion.button>
            </form>
          </motion.div>

          {/* Service Description */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="backdrop-blur-sm   bg-[#ffffffad] p-6 rounded-lg shadow-lg"
          >
            <div className="">
              {cartLoading ? (
                <div className="animate-pulse">
                  <div className="h-4 bg-gray-300 rounded w-3/4 mb-2"></div>
                  <div className="h-4 bg-gray-300 rounded w-1/2 mb-2"></div>
                  <div className="h-4 bg-gray-300 rounded w-5/6"></div>
                </div>
              ) : (
                <div
                  className="text-gray-700 leading-relaxed prose prose-sm max-w-none"
                  dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(cartInfo?.html || 'What are you paying for?') }}
                />
              )}
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default CartPage;

