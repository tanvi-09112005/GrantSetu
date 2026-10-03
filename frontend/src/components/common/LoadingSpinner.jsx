import React from 'react'
import { Loader2 } from 'lucide-react'

export default function LoadingSpinner({
  size = 'md',
  message = 'Loading...',
  fullScreen = false,
  className = '',
}) {
  const sizeMap = {
    sm: 'size-4',
    md: 'size-6',
    lg: 'size-10',
    xl: 'size-14',
  }

  const spinner = (
    <div className={`flex flex-col items-center justify-center gap-3 p-6 text-neutral-600 ${className}`}>
      <Loader2 className={`${sizeMap[size] || sizeMap.md} animate-spin text-indigo-600`} />
      {message && <p className="text-xs font-medium text-neutral-500 tracking-wide animate-pulse">{message}</p>}
    </div>
  )

  if (fullScreen) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-white/80 backdrop-blur-xs">
        {spinner}
      </div>
    )
  }

  return spinner
}
