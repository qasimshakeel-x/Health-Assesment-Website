import React from 'react';
import {
  FaCircleCheck, FaCircleXmark, FaTriangleExclamation, FaLightbulb, FaRuler,
  FaDroplet, FaCircle, FaBrain, FaChartColumn, FaDumbbell, FaBowlFood, FaUtensils,
  FaScaleBalanced, FaHeart, FaStethoscope, FaBullseye, FaEgg, FaAppleWhole,
  FaSeedling, FaCalendarDays, FaSun, FaMoon, FaHand, FaMagnifyingGlass, FaClock,
  FaDrumstickBite, FaBowlRice, FaCandyCane, FaJar, FaHandFist, FaBriefcaseMedical,
  FaMugSaucer, FaClipboardList, FaCarrot, FaPhone, FaBreadSlice, FaGlassWater,
  FaMugHot, FaLeaf, FaStar, FaFish, FaWheatAwn, FaWineGlass, FaFaceSmile, FaArrowRight,
} from 'react-icons/fa6';

// Backend chat replies (backend/app/routes/chat.py) ke emojis → Font Awesome 6 icons.
// NOTE: keys variation-selector (U+FE0F) ke BINA likhe hain — input normalize karne se
// "⚠️" aur "⚠" dono match ho jaate hain. Value = [icon, tailwind color class].
const EMOJI_ICONS = {
  '✅': [FaCircleCheck, 'text-green-400'],
  '❌': [FaCircleXmark, 'text-red-400'],
  '⚠': [FaTriangleExclamation, 'text-yellow-400'],
  '💡': [FaLightbulb, 'text-yellow-300'],
  '📏': [FaRuler, 'text-gray-400'],
  '🩸': [FaDroplet, 'text-red-400'],
  '🟢': [FaCircle, 'text-green-400'],
  '🟡': [FaCircle, 'text-yellow-400'],
  '🟠': [FaCircle, 'text-orange-400'],
  '🔴': [FaCircle, 'text-red-400'],
  '🧠': [FaBrain, 'text-pink-300'],
  '📊': [FaChartColumn, 'text-primary-300'],
  '🏋': [FaDumbbell, 'text-primary-300'],
  '🥗': [FaBowlFood, 'text-green-300'],
  '🍽': [FaUtensils, 'text-gray-300'],
  '💧': [FaDroplet, 'text-blue-400'],
  '⚖': [FaScaleBalanced, 'text-primary-300'],
  '❤': [FaHeart, 'text-red-400'],
  '💚': [FaHeart, 'text-green-400'],
  '🩺': [FaStethoscope, 'text-primary-300'],
  '🎯': [FaBullseye, 'text-red-400'],
  '🍳': [FaEgg, 'text-yellow-200'],
  '🍎': [FaAppleWhole, 'text-red-400'],
  '🥜': [FaSeedling, 'text-amber-300'],
  '🗓': [FaCalendarDays, 'text-primary-300'],
  '🌅': [FaSun, 'text-orange-300'],
  '🌙': [FaMoon, 'text-indigo-300'],
  '🌜': [FaMoon, 'text-indigo-300'],
  '👋': [FaHand, 'text-yellow-300'],
  '🔍': [FaMagnifyingGlass, 'text-primary-300'],
  '🫐': [FaSeedling, 'text-purple-300'],
  '🥚': [FaEgg, 'text-yellow-200'],
  '🥑': [FaSeedling, 'text-green-400'],
  '⏰': [FaClock, 'text-primary-300'],
  '🥩': [FaDrumstickBite, 'text-red-300'],
  '🍚': [FaBowlRice, 'text-gray-300'],
  '🍬': [FaCandyCane, 'text-pink-300'],
  '🧂': [FaJar, 'text-gray-300'],
  '💪': [FaHandFist, 'text-orange-300'],
  '⚕': [FaBriefcaseMedical, 'text-primary-300'],
  '🫖': [FaMugSaucer, 'text-amber-300'],
  '📋': [FaClipboardList, 'text-primary-300'],
  '🥕': [FaCarrot, 'text-orange-400'],
  '📞': [FaPhone, 'text-primary-300'],
  '🍞': [FaBreadSlice, 'text-amber-300'],
  '🥛': [FaGlassWater, 'text-gray-200'],
  '☕': [FaMugHot, 'text-amber-400'],
  '🥦': [FaLeaf, 'text-green-400'],
  '🌟': [FaStar, 'text-yellow-300'],
  '🐟': [FaFish, 'text-blue-300'],
  '🥬': [FaLeaf, 'text-green-300'],
  '🫘': [FaSeedling, 'text-amber-400'],
  '🫒': [FaSeedling, 'text-green-500'],
  '🌾': [FaWheatAwn, 'text-amber-300'],
  '🧄': [FaSeedling, 'text-gray-300'],
  '🍷': [FaWineGlass, 'text-red-400'],
  '😊': [FaFaceSmile, 'text-yellow-300'],
  '→': [FaArrowRight, 'text-gray-500'],
};

// Longest sequence pehle — taake multi-codepoint emojis base char se pehle match hon.
const EMOJI_RE = new RegExp(
  '(' +
    Object.keys(EMOJI_ICONS)
      .sort((a, b) => b.length - a.length)
      .map((e) => e.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
      .join('|') +
    ')',
  'g'
);

// Map mein na hone wale koi bhi bache hue emoji — strip kar do (LLM apne emojis bhi bhej sakta hai).
const STRAY_EMOJI_RE =
  /[\u{1F000}-\u{1FAFF}\u{2190}-\u{21FF}\u{2300}-\u{27BF}\u{2B00}-\u{2BFF}\u{2600}-\u{26FF}]/gu;

const ICON_STYLE = { verticalAlign: '-0.125em' };

/**
 * Text ke andar ke emojis ko Font Awesome icons mein badal kar render karta hai.
 * Variation selector (U+FE0F) normalize karke match karta hai.
 */
export default function EmojiText({ text }) {
  if (text == null || text === '') return null;
  const clean = String(text).replace(/\uFE0F/g, '');

  return clean.split(EMOJI_RE).map((piece, i) => {
    if (piece === '') return null;
    const entry = EMOJI_ICONS[piece];
    if (entry) {
      const [Icon, color] = entry;
      return (
        <Icon
          key={i}
          className={`inline ${color}`}
          style={ICON_STYLE}
          size={13}
          aria-hidden="true"
        />
      );
    }
    const stripped = piece.replace(STRAY_EMOJI_RE, '');
    if (stripped === '') return null;
    return <React.Fragment key={i}>{stripped}</React.Fragment>;
  });
}
