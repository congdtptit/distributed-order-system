import { P2_ARCH_DIAGRAMS } from "./diagrams_p2_arch.mjs";
import { P2_ACT_DIAGRAMS } from "./diagrams_p2_act.mjs";
import { P4_DIAGRAMS } from "./diagrams_p4.mjs";

export const DIAGRAMS = [
  {
    name: "hinh-1-1-bai-toan-da-kenh",
    width: 1120,
    scale: 2,
    body: `
      <style>
        .h1-wrap {
          border: 1.5px solid #cbd5e1;
          border-radius: 14px;
          padding: 20px 22px 16px;
          background: #ffffff;
        }
        .h1-title {
          text-align: center;
          font-size: 17px;
          font-weight: 700;
          color: #0f172a;
          margin-bottom: 16px;
          letter-spacing: 0.2px;
        }
        .h1-grid {
          position: relative;
          display: grid;
          grid-template-columns: 1fr 64px 1.24fr 64px 1.08fr;
          grid-template-rows: auto 1fr;
          align-items: stretch;
        }
        .col-head {
          font-size: 12px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: #475569;
          text-align: center;
          padding-bottom: 10px;
          grid-row: 1;
        }
        .col-head.left { grid-column: 1; }
        .col-head.mid { grid-column: 3; color: #991b1b; }
        .col-head.right { grid-column: 5; }
        .col-cards {
          grid-row: 2;
          display: flex;
          flex-direction: column;
          justify-content: center;
          gap: 18px;
          position: relative;
          z-index: 2;
        }
        .col-cards.left { grid-column: 1; gap: 22px; }
        .col-cards.right { grid-column: 5; gap: 26px; }
        .card {
          border-radius: 10px;
          padding: 13px 15px;
          background: #f8fafc;
          border: 1.5px solid #94a3b8;
          box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }
        .card.blue { border-color: #2563eb; background: #eff6ff; }
        .card.teal { border-color: #0d9488; background: #f0fdfa; }
        .card.amber { border-color: #d97706; background: #fffbeb; }
        .card.purple { border-color: #7c3aed; background: #f5f3ff; }
        .card.slate { border-color: #334155; background: #f8fafc; }
        .badge {
          display: inline-block;
          font-size: 11px;
          font-weight: 700;
          color: #ffffff;
          padding: 2px 9px;
          border-radius: 999px;
          margin-bottom: 7px;
        }
        .blue .badge { background: #1d4ed8; }
        .teal .badge { background: #0f766e; }
        .amber .badge { background: #b45309; }
        .purple .badge { background: #6d28d9; }
        .slate .badge { background: #334155; }
        .card h4 {
          font-size: 14px;
          font-weight: 700;
          color: #0f172a;
          margin-bottom: 5px;
        }
        .card p {
          font-size: 12.5px;
          line-height: 1.45;
          color: #334155;
        }
        .risk-panel {
          grid-row: 2;
          grid-column: 3;
          border: 1.5px dashed #dc2626;
          border-radius: 12px;
          padding: 13px 15px;
          background: #fef2f2;
          display: flex;
          flex-direction: column;
          justify-content: center;
          gap: 10px;
          position: relative;
          z-index: 2;
        }
        .risk-item {
          background: #ffffff;
          border: 1px solid #fca5a5;
          border-radius: 8px;
          padding: 9px 11px;
        }
        .risk-item strong {
          display: block;
          font-size: 12.5px;
          color: #b91c1c;
          margin-bottom: 3px;
        }
        .risk-item span {
          display: block;
          font-size: 12px;
          line-height: 1.42;
          color: #334155;
        }
        .h1-svg {
          position: absolute;
          inset: 0;
          width: 100%;
          height: 100%;
          pointer-events: none;
          z-index: 3;
          overflow: visible;
        }
        .h1-legend {
          margin-top: 14px;
          padding: 9px 14px;
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 9px;
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 22px;
          font-size: 11.5px;
          color: #334155;
        }
        .h1-leg-item {
          display: flex;
          align-items: center;
          gap: 7px;
          white-space: nowrap;
        }
      </style>
      <div class="h1-wrap">
        <div class="h1-title">BÀI TOÁN HỢP NHẤT ĐẶT HÀNG ĐA KÊNH VÀ CÁC ĐIỂM NGHẼN PHÂN TÁN</div>
        <div class="h1-grid" id="h1-grid">
          <div class="col-head left">1. Nguồn phát sinh đơn độc lập</div>
          <div class="col-head mid">Điểm nghẽn truyền thông &amp; tranh chấp</div>
          <div class="col-head right">2. Xử lý &amp; tổng hợp trung tâm</div>

          <div class="col-cards left">
            <div class="card blue" id="c-pos">
              <span class="badge">Tại quầy (POS01, POS02)</span>
              <h4>Điểm bán trực tiếp</h4>
              <p>Thu ngân lập đơn tại quầy, gửi yêu cầu hủy khi khách đổi ý và vẫn phải nhận đơn khi đứt mạng ra trung tâm.</p>
            </div>
            <div class="card teal" id="c-online">
              <span class="badge">Đặt trực tuyến (Online)</span>
              <h4>Kênh đặt hàng từ xa</h4>
              <p>Tiếp nhận đơn hàng chạy trên tiến trình riêng, phát sinh đơn đồng thời với các quầy bán hàng trực tiếp.</p>
            </div>
          </div>

          <div class="risk-panel" id="c-risk">
            <div class="risk-item">
              <strong>1. Chi nhánh mất kết nối mạng</strong>
              <span>Đơn tạo cục bộ chưa tới Bếp/Kho; thu ngân cần biết rõ đơn đã gửi đi hay chưa trước khi chốt hủy.</span>
            </div>
            <div class="risk-item">
              <strong>2. Xung đột nguyên liệu &amp; trạng thái</strong>
              <span>Hai nguồn cùng đặt món dùng chung nguyên liệu tồn hạn chế; yêu cầu hủy trùng lúc Bếp bắt đầu nấu.</span>
            </div>
            <div class="risk-item">
              <strong>3. Tin nhắn lặp hoặc sai thứ tự</strong>
              <span>Mạng chập chờn làm lặp gói tạo đơn hoặc đẩy lệnh hủy tới Bếp trước thông điệp đơn hàng.</span>
            </div>
            <div class="risk-item">
              <strong>4. Độ trễ tổng hợp số liệu</strong>
              <span>Báo cáo quản lý gom từ nhiều nguồn cần hiển thị rõ mốc dữ liệu tính đến cho từng kênh.</span>
            </div>
          </div>

          <div class="col-cards right">
            <div class="card amber" id="c-inv">
              <span class="badge">Kho trung tâm</span>
              <h4>Giữ &amp; kiểm soát nguyên liệu</h4>
              <p>Giữ đủ nguyên liệu cho cả đơn hoặc từ chối toàn bộ, tránh giữ trùng và chặn món khi nguyên liệu hỏng.</p>
            </div>
            <div class="card purple" id="c-kit">
              <span class="badge">Bếp trung tâm</span>
              <h4>Hợp nhất phiếu &amp; phân xử hủy</h4>
              <p>Nhận phiếu từ cả POS và Online, điều phối chế biến và quyết định duy nhất khi có tranh chấp hủy đơn.</p>
            </div>
            <div class="card slate" id="c-rep">
              <span class="badge">Tổng hợp trung tâm</span>
              <h4>Báo cáo hợp nhất gần thời gian thực</h4>
              <p>Gom trạng thái đơn từ tất cả nguồn độc lập kèm mốc thời gian cập nhật của từng kênh.</p>
            </div>
          </div>

          <svg class="h1-svg" id="h1-svg" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <marker id="arrFwd" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                <path d="M0,1 L7,4 L0,7 Z" fill="#475569"/>
              </marker>
              <marker id="arrRet" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                <path d="M0,1 L7,4 L0,7 Z" fill="#6d28d9"/>
              </marker>
              <marker id="arrStep" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                <path d="M0,1 L7,4 L0,7 Z" fill="#b45309"/>
              </marker>
            </defs>
          </svg>
        </div>

        <div class="h1-legend">
          <div class="h1-leg-item">
            <svg width="32" height="12" viewBox="0 0 32 12"><line x1="2" y1="6" x2="28" y2="6" stroke="#475569" stroke-width="2" marker-end="url(#arrFwd)"/></svg>
            <span>Đơn hàng, yêu cầu hủy &amp; đồng bộ qua mạng</span>
          </div>
          <div class="h1-leg-item">
            <svg width="32" height="12" viewBox="0 0 32 12"><line x1="2" y1="6" x2="28" y2="6" stroke="#6d28d9" stroke-width="1.8" stroke-dasharray="4,3" marker-end="url(#arrRet)"/></svg>
            <span>Phản hồi giữ kho, phân xử hủy &amp; trạng thái</span>
          </div>
          <div class="h1-leg-item">
            <svg width="32" height="12" viewBox="0 0 32 12"><line x1="2" y1="6" x2="28" y2="6" stroke="#b45309" stroke-width="2" marker-end="url(#arrStep)"/></svg>
            <span>Chuyển phiếu Bếp khi giữ đủ nguyên liệu</span>
          </div>
        </div>
      </div>
      <script>
        (() => {
          const grid = document.getElementById('h1-grid');
          const svg = document.getElementById('h1-svg');
          const gRect = grid.getBoundingClientRect();
          svg.setAttribute('viewBox', '0 0 ' + gRect.width + ' ' + gRect.height);

          const box = (id) => {
            const r = document.getElementById(id).getBoundingClientRect();
            return {
              l: r.left - gRect.left,
              r: r.right - gRect.left,
              t: r.top - gRect.top,
              b: r.bottom - gRect.top,
              cx: (r.left + r.right) / 2 - gRect.left,
              cy: (r.top + r.bottom) / 2 - gRect.top,
            };
          };

          const pos = box('c-pos');
          const online = box('c-online');
          const risk = box('c-risk');
          const inv = box('c-inv');
          const kit = box('c-kit');
          const rep = box('c-rep');

          const addPath = (d, stroke, marker, dashed = false) => {
            const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            p.setAttribute('d', d);
            p.setAttribute('fill', 'none');
            p.setAttribute('stroke', stroke);
            p.setAttribute('stroke-width', dashed ? '1.8' : '2');
            if (dashed) p.setAttribute('stroke-dasharray', '5,4');
            if (marker) p.setAttribute('marker-end', 'url(#' + marker + ')');
            svg.appendChild(p);
          };

          const bezierH = (x1, y1, x2, y2) => {
            const mx = (x1 + x2) / 2;
            return 'M' + x1.toFixed(1) + ',' + y1.toFixed(1) +
                   ' C' + mx.toFixed(1) + ',' + y1.toFixed(1) +
                   ' ' + mx.toFixed(1) + ',' + y2.toFixed(1) +
                   ' ' + x2.toFixed(1) + ',' + y2.toFixed(1);
          };

          // Left <-> Risk (parallel forward & return arrows anchored to exact card centers)
          const posRiskY = pos.cy * 0.72 + risk.cy * 0.28;
          addPath(bezierH(pos.r + 2, pos.cy - 6, risk.l - 3, posRiskY - 6), '#475569', 'arrFwd');
          addPath(bezierH(risk.l - 2, posRiskY + 6, pos.r + 3, pos.cy + 6), '#6d28d9', 'arrRet', true);

          const onlRiskY = online.cy * 0.72 + risk.cy * 0.28;
          addPath(bezierH(online.r + 2, online.cy - 6, risk.l - 3, onlRiskY - 6), '#475569', 'arrFwd');
          addPath(bezierH(risk.l - 2, onlRiskY + 6, online.r + 3, online.cy + 6), '#6d28d9', 'arrRet', true);

          // Risk <-> Kho, Bếp; Risk -> Tổng hợp
          const invRiskY = inv.cy * 0.68 + risk.cy * 0.32;
          addPath(bezierH(risk.r + 2, invRiskY - 6, inv.l - 3, inv.cy - 6), '#475569', 'arrFwd');
          addPath(bezierH(inv.l - 2, inv.cy + 6, risk.r + 3, invRiskY + 6), '#6d28d9', 'arrRet', true);

          addPath(bezierH(risk.r + 2, kit.cy - 6, kit.l - 3, kit.cy - 6), '#475569', 'arrFwd');
          addPath(bezierH(kit.l - 2, kit.cy + 6, risk.r + 3, kit.cy + 6), '#6d28d9', 'arrRet', true);

          const repRiskY = rep.cy * 0.68 + risk.cy * 0.32;
          addPath(bezierH(risk.r + 2, repRiskY, rep.l - 3, rep.cy), '#475569', 'arrFwd');

          // Kho -> Bếp sequential handoff arrow
          addPath('M' + inv.cx.toFixed(1) + ',' + (inv.b + 2).toFixed(1) + ' L' + kit.cx.toFixed(1) + ',' + (kit.t - 3).toFixed(1), '#b45309', 'arrStep');
        })();
      </script>
    `,
  },
  ...P2_ARCH_DIAGRAMS,
  ...P2_ACT_DIAGRAMS,
  ...P4_DIAGRAMS,
];
