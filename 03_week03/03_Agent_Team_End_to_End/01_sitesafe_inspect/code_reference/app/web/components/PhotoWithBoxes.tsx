'use client';

// Draws bounding boxes over the original photo from stored coordinates (D-08).
// Supports toggling All PPE (Hardhat, Safety Vest, NO-Hardhat, NO-Safety Vest) vs Violations only.

import { useState } from 'react';

export type Detection = {
  id: number;
  cls: string;
  label: string;
  confidence: number;
  box: [number, number, number, number];
};

const VIOLATION_CLS = new Set(['NO_HARDHAT', 'NO_VEST']);

export default function PhotoWithBoxes({
  src,
  alt,
  imageW,
  imageH,
  detections,
}: {
  src: string;
  alt: string;
  imageW: number | null;
  imageH: number | null;
  detections: Detection[];
}) {
  const [natural, setNatural] = useState<{ w: number; h: number } | null>(null);
  const [failed, setFailed] = useState(false);
  const [showPositive, setShowPositive] = useState(true);

  const positiveCount = detections.filter((d) => !VIOLATION_CLS.has(d.cls)).length;
  const violationCount = detections.filter((d) => VIOLATION_CLS.has(d.cls)).length;
  const visible = showPositive ? detections : detections.filter((d) => VIOLATION_CLS.has(d.cls));

  const extentW = Math.max(1, ...detections.map((d) => Math.max(d.box[0], d.box[2])));
  const extentH = Math.max(1, ...detections.map((d) => Math.max(d.box[1], d.box[3])));
  const w = imageW ?? natural?.w ?? extentW;
  const h = imageH ?? natural?.h ?? extentH;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-red-100 text-red-800 px-2.5 py-1 font-semibold">
            <span className="h-2 w-2 rounded-full bg-red-600" />
            จุดผิดปกติ ({violationCount})
          </span>
          {positiveCount > 0 && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 text-emerald-800 px-2.5 py-1 font-semibold">
              <span className="h-2 w-2 rounded-full bg-emerald-600" />
              สวมอุปกรณ์ครบ ({positiveCount})
            </span>
          )}
        </div>
        {positiveCount > 0 && (
          <button
            type="button"
            className="secondary py-1 px-3 text-xs"
            data-testid="toggle-positive-boxes"
            onClick={() => setShowPositive((s) => !s)}
          >
            {showPositive ? 'ซ่อนกรอบที่สวมครบ' : 'แสดงอุปกรณ์ทั้งหมด'}
          </button>
        )}
      </div>

      <div className="photo-frame">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          data-testid="photo-image"
          src={src}
          alt={alt}
          onLoad={(e) => setNatural({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })}
          onError={() => setFailed(true)}
        />
        {failed && (
          <p className="error m-3" style={{ lineHeight: 1.5 }}>
            เปิดไฟล์รูปไม่ได้
          </p>
        )}
        {w > 0 &&
          h > 0 &&
          visible.map((d, i) => {
            const [x1, y1, x2, y2] = d.box;
            const left = (Math.min(x1, x2) / w) * 100;
            const top = (Math.min(y1, y2) / h) * 100;
            const width = (Math.abs(x2 - x1) / w) * 100;
            const height = (Math.abs(y2 - y1) / h) * 100;
            return (
              <div
                key={d.id}
                className={`photo-box ${d.cls}`}
                data-testid={`photo-box-${i}`}
                data-cls={d.cls}
                style={{ left: `${left}%`, top: `${top}%`, width: `${width}%`, height: `${height}%` }}
                title={`${d.label} (${(d.confidence * 100).toFixed(0)}%)`}
              >
                <span className="label" data-testid={`photo-box-label-${i}`}>
                  {d.label} {(d.confidence * 100).toFixed(0)}%
                </span>
              </div>
            );
          })}
      </div>
    </div>
  );
}
