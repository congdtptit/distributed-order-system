import { buildErdDiagram } from "./erd_svg.mjs";

export const P2_ARCH_DIAGRAMS = [
  {
    name: "hinh-2-1-mo-hinh-hld",
    width: 980,
    scale: 2,
    body: `
      <div style="border:1.5px solid #cbd5e1;border-radius:14px;background:#ffffff;padding:12px;">
        <svg width="956" height="1010" viewBox="0 0 956 1010" xmlns="http://www.w3.org/2000/svg" style="display:block;font-family:'Segoe UI',Arial,sans-serif;">
          <defs>
            <marker id="hArrG" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
              <path d="M0,1 L7,4 L0,7" fill="none" stroke="#475569" stroke-width="1.6"/>
            </marker>
            <marker id="hArrP" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
              <path d="M0,1 L7,4 L0,7" fill="none" stroke="#6d28d9" stroke-width="1.6"/>
            </marker>
          </defs>

          <!-- ==================== 1. ORDER SOURCES (GREEN) ==================== -->
          <rect x="16" y="12" width="876" height="296" rx="14" fill="#edf7f1" stroke="#15803d" stroke-width="1.6"/>
          <text x="454" y="36" text-anchor="middle" font-size="14" font-weight="700" fill="#14532d">Order sources (Các nguồn đặt hàng độc lập)</text>

          <!-- Left: POS sites -->
          <rect x="34" y="48" width="404" height="244" rx="11" fill="#e5ece8" stroke="#94a3b8" stroke-width="1.2"/>
          <text x="236" y="69" text-anchor="middle" font-size="13" font-weight="700" fill="#0f172a">POS sites (Quầy 01, Quầy 02)</text>

          <rect x="108" y="80" width="256" height="32" rx="7" fill="#e0f2fe" stroke="#0d9488" stroke-width="1.2"/>
          <text x="236" y="100" text-anchor="middle" font-size="12.5" font-weight="600" fill="#0f172a">POS Application (Màn hình thu ngân)</text>
          <line x1="236" y1="112" x2="236" y2="128" stroke="#475569" stroke-width="1.5" marker-end="url(#hArrG)"/>

          <rect x="108" y="130" width="256" height="40" rx="7" fill="#dcfce7" stroke="#0d9488" stroke-width="1.2"/>
          <text x="236" y="148" text-anchor="middle" font-size="12.5" font-weight="700" fill="#0f172a">Local Order Service</text>
          <text x="236" y="164" text-anchor="middle" font-size="11" fill="#334155">×1 instance độc lập mỗi quầy</text>
          <line x1="236" y1="170" x2="236" y2="186" stroke="#475569" stroke-width="1.5" marker-end="url(#hArrG)"/>

          <rect x="52" y="188" width="368" height="90" rx="9" fill="#d6dad5" stroke="#94a3b8" stroke-width="1.2"/>
          <text x="236" y="208" text-anchor="middle" font-size="12.5" font-weight="700" fill="#0f172a">Local Order DB (CSDL từng quầy)</text>
          <rect x="68" y="218" width="156" height="46" rx="7" fill="#faf8f5" stroke="#94a3b8"/>
          <text x="146" y="245" text-anchor="middle" font-size="12" font-family="'Consolas',monospace" font-weight="600" fill="#0f172a">outbox_events</text>
          <rect x="242" y="218" width="162" height="46" rx="7" fill="#faf8f5" stroke="#94a3b8"/>
          <text x="323" y="238" text-anchor="middle" font-size="12" font-weight="700" fill="#0f172a">POS orders</text>
          <text x="323" y="254" text-anchor="middle" font-size="11" fill="#475569">Đơn tại quầy &amp; thực đơn</text>

          <!-- Right: Online site -->
          <rect x="470" y="48" width="404" height="244" rx="11" fill="#e5ece8" stroke="#94a3b8" stroke-width="1.2"/>
          <text x="672" y="69" text-anchor="middle" font-size="13" font-weight="700" fill="#0f172a">Online site (Kênh trực tuyến)</text>

          <rect x="544" y="80" width="256" height="32" rx="7" fill="#e0f2fe" stroke="#0d9488" stroke-width="1.2"/>
          <text x="672" y="100" text-anchor="middle" font-size="12.5" font-weight="600" fill="#0f172a">Web Application (Đặt món trực tuyến)</text>
          <line x1="672" y1="112" x2="672" y2="128" stroke="#475569" stroke-width="1.5" marker-end="url(#hArrG)"/>

          <rect x="544" y="130" width="256" height="40" rx="7" fill="#dcfce7" stroke="#0d9488" stroke-width="1.2"/>
          <text x="672" y="148" text-anchor="middle" font-size="12.5" font-weight="700" fill="#0f172a">Online Order Service</text>
          <text x="672" y="164" text-anchor="middle" font-size="11" fill="#334155">Tiến trình tách biệt với quầy</text>
          <line x1="672" y1="170" x2="672" y2="186" stroke="#475569" stroke-width="1.5" marker-end="url(#hArrG)"/>

          <rect x="488" y="188" width="368" height="90" rx="9" fill="#d6dad5" stroke="#94a3b8" stroke-width="1.2"/>
          <text x="672" y="208" text-anchor="middle" font-size="12.5" font-weight="700" fill="#0f172a">Online Order DB (CSDL kênh Online)</text>
          <rect x="504" y="218" width="162" height="46" rx="7" fill="#faf8f5" stroke="#94a3b8"/>
          <text x="585" y="238" text-anchor="middle" font-size="12" font-weight="700" fill="#0f172a">Online orders</text>
          <text x="585" y="254" text-anchor="middle" font-size="11" fill="#475569">Đơn online &amp; thực đơn</text>
          <rect x="684" y="218" width="156" height="46" rx="7" fill="#faf8f5" stroke="#94a3b8"/>
          <text x="762" y="245" text-anchor="middle" font-size="12" font-family="'Consolas',monospace" font-weight="600" fill="#0f172a">outbox_events</text>

          <!-- ==================== 2. CENTRAL DATA SITE (GREY) ==================== -->
          <rect x="184" y="346" width="540" height="162" rx="13" fill="#f1f2f0" stroke="#64748b" stroke-width="1.4"/>
          <text x="204" y="492" font-size="13" font-weight="700" fill="#1e293b">Central data site (Tổng hợp dữ liệu toàn hệ thống)</text>

          <rect x="206" y="384" width="212" height="58" rx="9" fill="#faf8f5" stroke="#94a3b8" stroke-width="1.3"/>
          <text x="312" y="409" text-anchor="middle" font-size="12.5" font-weight="700" fill="#0f172a">Central Order Replica</text>
          <text x="312" y="427" text-anchor="middle" font-size="11" fill="#475569">Bản sao hợp nhất các nguồn</text>

          <line x1="418" y1="413" x2="462" y2="413" stroke="#475569" stroke-width="1.5" marker-end="url(#hArrG)"/>

          <rect x="464" y="362" width="242" height="48" rx="8" fill="#dcfce7" stroke="#0d9488" stroke-width="1.2"/>
          <text x="585" y="383" text-anchor="middle" font-size="12.5" font-weight="700" fill="#0f172a">Order Query Service</text>
          <text x="585" y="399" text-anchor="middle" font-size="11" fill="#334155">Truy vấn tổng hợp nhất quán</text>

          <line x1="585" y1="410" x2="585" y2="428" stroke="#475569" stroke-width="1.5" marker-end="url(#hArrG)"/>

          <rect x="464" y="430" width="242" height="36" rx="8" fill="#e0f2fe" stroke="#0d9488" stroke-width="1.2"/>
          <text x="585" y="453" text-anchor="middle" font-size="12.5" font-weight="600" fill="#0f172a">Dashboard Báo cáo quản lý</text>

          <!-- Dashed Logical Replication arrows: POS orders & Online orders -> Central Order Replica -->
          <path d="M 323,264 L 323,382" fill="none" stroke="#475569" stroke-width="1.6" stroke-dasharray="5,4" marker-end="url(#hArrG)"/>
          <path d="M 585,264 L 585,326 L 352,326 L 352,382" fill="none" stroke="#475569" stroke-width="1.6" stroke-dasharray="5,4" marker-end="url(#hArrG)"/>
          <rect x="392" y="315" width="170" height="20" rx="5" fill="#ffffff" stroke="#cbd5e1"/>
          <text x="477" y="329" text-anchor="middle" font-size="11" font-weight="600" fill="#334155">Nhân bản DB bất đồng bộ</text>

          <!-- ==================== 3. KAFKA CLUSTER (LAVENDER) ==================== -->
          <rect x="16" y="548" width="876" height="114" rx="14" fill="#f3f0fc" stroke="#7c3aed" stroke-width="1.6"/>
          <text x="454" y="572" text-anchor="middle" font-size="14" font-weight="700" fill="#4c1d95">Kafka cluster · 3 broker (truyền tin bất đồng bộ)</text>

          <rect x="38" y="586" width="268" height="60" rx="9" fill="#e8ebfd" stroke="#7c3aed" stroke-width="1.2"/>
          <text x="172" y="611" text-anchor="middle" font-size="12.5" font-weight="700" fill="#0f172a">Order &amp; Cancel events</text>
          <text x="172" y="631" text-anchor="middle" font-size="11" fill="#475569">Sự kiện tạo đơn &amp; yêu cầu hủy</text>

          <rect x="330" y="586" width="256" height="60" rx="9" fill="#e8ebfd" stroke="#7c3aed" stroke-width="1.2"/>
          <text x="458" y="611" text-anchor="middle" font-size="12.5" font-weight="700" fill="#0f172a">Processing &amp; Menu events</text>
          <text x="458" y="631" text-anchor="middle" font-size="11" fill="#475569">Giữ kho · Hoàn kho · Cập nhật thực đơn</text>

          <rect x="610" y="586" width="262" height="60" rx="9" fill="#e8ebfd" stroke="#7c3aed" stroke-width="1.2"/>
          <text x="741" y="611" text-anchor="middle" font-size="12.5" font-weight="700" fill="#0f172a">Status events</text>
          <text x="741" y="631" text-anchor="middle" font-size="11" fill="#475569">Đã giữ kho · Hết hàng · Hủy · Hoàn tất</text>

          <!-- Arrows Sources -> Kafka -->
          <path d="M 146,264 L 146,584" fill="none" stroke="#475569" stroke-width="1.6" marker-end="url(#hArrG)"/>
          <path d="M 762,264 L 762,526 L 232,526 L 232,584" fill="none" stroke="#475569" stroke-width="1.6" marker-end="url(#hArrG)"/>

          <!-- Purple return path: Status & Menu events -> Order sources (clean outer right rail) -->
          <path d="M 872,616 L 922,616 L 922,152 L 894,152" fill="none" stroke="#6d28d9" stroke-width="1.8" marker-end="url(#hArrP)"/>

          <!-- ==================== 4. CENTRAL PROCESSING (AMBER) ==================== -->
          <rect x="16" y="704" width="876" height="248" rx="14" fill="#fbf5e8" stroke="#b45309" stroke-width="1.6"/>
          <text x="250" y="727" text-anchor="middle" font-size="13.5" font-weight="700" fill="#78350f">Central processing (Kho &amp; Bếp trung tâm)</text>

          <!-- Left: Central warehouse site -->
          <rect x="34" y="740" width="404" height="196" rx="11" fill="#efe9df" stroke="#94a3b8" stroke-width="1.2"/>
          <text x="236" y="761" text-anchor="middle" font-size="13" font-weight="700" fill="#0f172a">Central warehouse site (Kho trung tâm)</text>

          <rect x="108" y="772" width="256" height="40" rx="7" fill="#dcfce7" stroke="#0d9488" stroke-width="1.2"/>
          <text x="236" y="790" text-anchor="middle" font-size="12.5" font-weight="700" fill="#0f172a">Inventory Service</text>
          <text x="236" y="806" text-anchor="middle" font-size="11" fill="#334155">×2 instance xử lý giữ kho &amp; tồn kho</text>
          <line x1="236" y1="812" x2="236" y2="828" stroke="#475569" stroke-width="1.5" marker-end="url(#hArrG)"/>

          <rect x="52" y="830" width="360" height="90" rx="9" fill="#d8d4cc" stroke="#94a3b8" stroke-width="1.2"/>
          <text x="232" y="850" text-anchor="middle" font-size="12.5" font-weight="700" fill="#0f172a">Inventory DB</text>
          <rect x="64" y="860" width="166" height="46" rx="7" fill="#faf8f5" stroke="#94a3b8"/>
          <text x="147" y="880" text-anchor="middle" font-size="12" font-weight="700" fill="#0f172a">Inventory data</text>
          <text x="147" y="896" text-anchor="middle" font-size="11" fill="#475569">Tồn kho, công thức &amp; món</text>
          <rect x="246" y="860" width="150" height="46" rx="7" fill="#faf8f5" stroke="#94a3b8"/>
          <text x="321" y="887" text-anchor="middle" font-size="12" font-family="'Consolas',monospace" font-weight="600" fill="#0f172a">outbox_events</text>

          <!-- Right: Central kitchen site -->
          <rect x="470" y="740" width="404" height="196" rx="11" fill="#efe9df" stroke="#94a3b8" stroke-width="1.2"/>
          <text x="672" y="761" text-anchor="middle" font-size="13" font-weight="700" fill="#0f172a">Central kitchen site (Bếp trung tâm)</text>

          <rect x="544" y="772" width="256" height="40" rx="7" fill="#dcfce7" stroke="#0d9488" stroke-width="1.2"/>
          <text x="672" y="790" text-anchor="middle" font-size="12.5" font-weight="700" fill="#0f172a">Kitchen Service</text>
          <text x="672" y="806" text-anchor="middle" font-size="11" fill="#334155">Hợp nhất phiếu nấu &amp; xử lý hủy</text>
          <line x1="672" y1="812" x2="672" y2="828" stroke="#475569" stroke-width="1.5" marker-end="url(#hArrG)"/>

          <rect x="488" y="830" width="356" height="90" rx="9" fill="#d8d4cc" stroke="#94a3b8" stroke-width="1.2"/>
          <text x="666" y="850" text-anchor="middle" font-size="12.5" font-weight="700" fill="#0f172a">Kitchen DB</text>
          <rect x="500" y="860" width="166" height="46" rx="7" fill="#faf8f5" stroke="#94a3b8"/>
          <text x="583" y="880" text-anchor="middle" font-size="12" font-weight="700" fill="#0f172a">Kitchen data</text>
          <text x="583" y="896" text-anchor="middle" font-size="11" fill="#475569">Phiếu bếp &amp; cảnh báo</text>
          <rect x="682" y="860" width="146" height="46" rx="7" fill="#faf8f5" stroke="#94a3b8"/>
          <text x="755" y="887" text-anchor="middle" font-size="12" font-family="'Consolas',monospace" font-weight="600" fill="#0f172a">outbox_events</text>

          <!-- Arrows Kafka <-> Central Processing -->
          <path d="M 74,646 L 74,792 L 106,792" fill="none" stroke="#475569" stroke-width="1.6" marker-end="url(#hArrG)"/>
          <text x="82" y="688" text-anchor="start" font-size="11" font-weight="600" fill="#334155">Đơn mới</text>

          <path d="M 396,883 L 424,883 L 424,648" fill="none" stroke="#475569" stroke-width="1.6" marker-end="url(#hArrG)"/>
          <text x="416" y="688" text-anchor="end" font-size="11" font-weight="600" fill="#334155">Giữ kho / Hết hàng / Thực đơn</text>

          <path d="M 504,646 L 504,792 L 542,792" fill="none" stroke="#475569" stroke-width="1.6" marker-end="url(#hArrG)"/>
          <text x="512" y="688" text-anchor="start" font-size="11" font-weight="600" fill="#334155">Đã giữ kho · Yêu cầu hủy</text>

          <path d="M 828,883 L 856,883 L 856,648" fill="none" stroke="#475569" stroke-width="1.6" marker-end="url(#hArrG)"/>
          <text x="848" y="688" text-anchor="end" font-size="11" font-weight="600" fill="#334155">Hoàn kho · Trạng thái đơn</text>

          <!-- ==================== 5. BOTTOM LEGEND ==================== -->
          <line x1="22" y1="984" x2="64" y2="984" stroke="#475569" stroke-width="1.8" marker-end="url(#hArrG)"/>
          <text x="74" y="988" font-size="12" fill="#334155">sự kiện truyền qua Kafka</text>

          <line x1="286" y1="984" x2="332" y2="984" stroke="#475569" stroke-width="1.8" stroke-dasharray="5,4" marker-end="url(#hArrG)"/>
          <text x="342" y="988" font-size="12" fill="#334155">nhân bản DB bất đồng bộ về trung tâm</text>

          <line x1="636" y1="984" x2="680" y2="984" stroke="#6d28d9" stroke-width="1.8" marker-end="url(#hArrP)"/>
          <text x="690" y="988" font-size="12" fill="#334155">trạng thái đơn &amp; thực đơn về nguồn</text>
        </svg>
      </div>
    `,
  },

  {
    name: "hinh-2-2-use-case-tong-quat",
    width: 1180,
    scale: 2,
    body: `
      <div style="border:1.5px solid #cbd5e1;border-radius:14px;padding:14px 16px;background:#ffffff;">
        <svg width="1148" height="720" viewBox="0 0 1148 720" xmlns="http://www.w3.org/2000/svg" style="display:block;font-family:'Segoe UI',Arial,sans-serif;">
          <defs>
            <marker id="ucArr" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto">
              <path d="M0,1 L8,4.5 L0,8" fill="none" stroke="#1d4ed8" stroke-width="1.5"/>
            </marker>
          </defs>

          <rect x="206" y="14" width="736" height="636" rx="14" fill="#fcfdff" stroke="#334155" stroke-width="2"/>
          <text x="574" y="42" text-anchor="middle" font-size="16" font-weight="700" fill="#0f172a">HỆ THỐNG ĐẶT HÀNG TẠI QUẦY VÀ ONLINE HỢP NHẤT</text>

          <!-- Left Actors -->
          <g transform="translate(88, 175)" stroke="#1d4ed8" stroke-width="2" fill="none">
            <circle cx="0" cy="-26" r="14"/>
            <line x1="0" y1="-12" x2="0" y2="20"/>
            <line x1="-18" y1="-2" x2="18" y2="-2"/>
            <line x1="0" y1="20" x2="-14" y2="44"/>
            <line x1="0" y1="20" x2="14" y2="44"/>
          </g>
          <text x="88" y="240" text-anchor="middle" font-size="13" font-weight="700" fill="#0f172a">Thu ngân tại quầy</text>
          <text x="88" y="257" text-anchor="middle" font-size="11.5" fill="#475569">(POS01, POS02)</text>

          <g transform="translate(88, 415)" stroke="#0f766e" stroke-width="2" fill="none">
            <circle cx="0" cy="-26" r="14"/>
            <line x1="0" y1="-12" x2="0" y2="20"/>
            <line x1="-18" y1="-2" x2="18" y2="-2"/>
            <line x1="0" y1="20" x2="-14" y2="44"/>
            <line x1="0" y1="20" x2="14" y2="44"/>
          </g>
          <text x="88" y="480" text-anchor="middle" font-size="13" font-weight="700" fill="#0f172a">Khách hàng Online</text>
          <text x="88" y="497" text-anchor="middle" font-size="11.5" fill="#475569">(Kênh trực tuyến)</text>

          <!-- Right Actors (evenly spaced, zero crossing through labels) -->
          <g transform="translate(1056, 108)" stroke="#b45309" stroke-width="2" fill="none">
            <circle cx="0" cy="-24" r="13"/>
            <line x1="0" y1="-11" x2="0" y2="18"/>
            <line x1="-16" y1="-1" x2="16" y2="-1"/>
            <line x1="0" y1="18" x2="-13" y2="40"/>
            <line x1="0" y1="18" x2="13" y2="40"/>
          </g>
          <text x="1056" y="168" text-anchor="middle" font-size="12.5" font-weight="700" fill="#0f172a">Nhân viên Kho</text>
          <text x="1056" y="184" text-anchor="middle" font-size="11" fill="#475569">(Kho trung tâm)</text>

          <g transform="translate(1056, 265)" stroke="#1d4ed8" stroke-width="2" fill="none">
            <rect x="-20" y="-28" width="40" height="32" rx="6" fill="#eff6ff"/>
            <line x1="-12" y1="-14" x2="12" y2="-14"/>
            <line x1="-12" y1="-6" x2="12" y2="-6"/>
            <line x1="0" y1="4" x2="0" y2="14"/>
            <line x1="-14" y1="14" x2="14" y2="14"/>
          </g>
          <text x="1056" y="300" text-anchor="middle" font-size="12" font-weight="700" fill="#1e3a8a">«system»</text>
          <text x="1056" y="316" text-anchor="middle" font-size="12" font-weight="700" fill="#0f172a">Xử lý sự kiện nền</text>
          <text x="1056" y="332" text-anchor="middle" font-size="11" fill="#475569">(Inventory / Kitchen)</text>

          <g transform="translate(1056, 430)" stroke="#6d28d9" stroke-width="2" fill="none">
            <circle cx="0" cy="-24" r="13"/>
            <line x1="0" y1="-11" x2="0" y2="18"/>
            <line x1="-16" y1="-1" x2="16" y2="-1"/>
            <line x1="0" y1="18" x2="-13" y2="40"/>
            <line x1="0" y1="18" x2="13" y2="40"/>
          </g>
          <text x="1056" y="490" text-anchor="middle" font-size="12.5" font-weight="700" fill="#0f172a">Nhân viên Bếp</text>
          <text x="1056" y="506" text-anchor="middle" font-size="11" fill="#475569">(Bếp trung tâm)</text>

          <g transform="translate(1056, 578)" stroke="#334155" stroke-width="2" fill="none">
            <circle cx="0" cy="-24" r="13"/>
            <line x1="0" y1="-11" x2="0" y2="18"/>
            <line x1="-16" y1="-1" x2="16" y2="-1"/>
            <line x1="0" y1="18" x2="-13" y2="40"/>
            <line x1="0" y1="18" x2="13" y2="40"/>
          </g>
          <text x="1056" y="638" text-anchor="middle" font-size="12.5" font-weight="700" fill="#0f172a">Quản lý chuỗi</text>
          <text x="1056" y="654" text-anchor="middle" font-size="11" fill="#475569">(Tổng hợp &amp; vận hành)</text>

          <!-- Left Column Use Cases (Module 1: UC-01..UC-03) -->
          <ellipse cx="378" cy="146" rx="142" ry="38" fill="#eff6ff" stroke="#1d4ed8" stroke-width="1.8"/>
          <text x="378" y="140" text-anchor="middle" font-size="12.5" font-weight="700" fill="#1e3a8a">UC-01: Xem thực đơn và đặt món</text>
          <text x="378" y="158" text-anchor="middle" font-size="11.2" fill="#334155">GD-01, GD-02 (Còn/Hết/Ẩn &amp; Outbox)</text>

          <ellipse cx="378" cy="296" rx="142" ry="38" fill="#f0fdfa" stroke="#0f766e" stroke-width="1.8"/>
          <text x="378" y="290" text-anchor="middle" font-size="12.5" font-weight="700" fill="#115e59">UC-02: Hủy đơn đặt món</text>
          <text x="378" y="308" text-anchor="middle" font-size="11.2" fill="#334155">GD-03 (Hủy tại chỗ hoặc chuyển Bếp)</text>

          <ellipse cx="378" cy="446" rx="142" ry="38" fill="#f0fdfa" stroke="#0f766e" stroke-width="1.8"/>
          <text x="378" y="440" text-anchor="middle" font-size="12.5" font-weight="700" fill="#115e59">UC-03: Theo dõi đơn và giám sát kênh</text>
          <text x="378" y="458" text-anchor="middle" font-size="11.2" fill="#334155">GD-04 (Thứ hạng trạng thái &amp; cảnh báo)</text>

          <!-- Right Column Use Cases (Modules 2, 3, 4: UC-04..UC-09) -->
          <ellipse cx="776" cy="106" rx="142" ry="34" fill="#fffbeb" stroke="#b45309" stroke-width="1.8"/>
          <text x="776" y="100" text-anchor="middle" font-size="12.5" font-weight="700" fill="#92400e">UC-05: Quản lý tồn kho</text>
          <text x="776" y="117" text-anchor="middle" font-size="11.2" fill="#334155">GD-07, GD-08, GD-09 (Tra cứu, nhập, kiểm)</text>

          <ellipse cx="776" cy="196" rx="142" ry="34" fill="#fffbeb" stroke="#b45309" stroke-width="1.8"/>
          <text x="776" y="190" text-anchor="middle" font-size="12.5" font-weight="700" fill="#92400e">UC-04: Xử lý nguyên liệu đơn đa nguồn</text>
          <text x="776" y="207" text-anchor="middle" font-size="11.2" fill="#334155">GD-05, GD-06 (Giữ kho, hoàn &amp; hao hụt)</text>

          <ellipse cx="776" cy="286" rx="142" ry="34" fill="#fffbeb" stroke="#b45309" stroke-width="1.8"/>
          <text x="776" y="280" text-anchor="middle" font-size="12.5" font-weight="700" fill="#92400e">UC-06: Đồng bộ trạng thái thực đơn</text>
          <text x="776" y="297" text-anchor="middle" font-size="11.2" fill="#334155">GD-10 (Công bố phiên bản &amp; snapshot)</text>

          <ellipse cx="776" cy="382" rx="142" ry="34" fill="#f5f3ff" stroke="#6d28d9" stroke-width="1.8"/>
          <text x="776" y="376" text-anchor="middle" font-size="12.5" font-weight="700" fill="#5b21b6">UC-07: Tiếp nhận đơn và phân xử hủy</text>
          <text x="776" y="393" text-anchor="middle" font-size="11.2" fill="#334155">GD-11 (Hợp nhất phiếu &amp; trọng tài hủy)</text>

          <ellipse cx="776" cy="478" rx="142" ry="34" fill="#f5f3ff" stroke="#6d28d9" stroke-width="1.8"/>
          <text x="776" y="472" text-anchor="middle" font-size="12.5" font-weight="700" fill="#5b21b6">UC-08: Xử lý phiếu chế biến</text>
          <text x="776" y="489" text-anchor="middle" font-size="11.2" fill="#334155">GD-12..GD-15 (Xem, nấu, từ chối, xong)</text>

          <ellipse cx="776" cy="578" rx="142" ry="34" fill="#f1f5f9" stroke="#334155" stroke-width="1.8"/>
          <text x="776" y="572" text-anchor="middle" font-size="12.5" font-weight="700" fill="#0f172a">UC-09: Xem báo cáo hợp nhất</text>
          <text x="776" y="589" text-anchor="middle" font-size="11.2" fill="#334155">GD-16 (Thống kê đa kênh &amp; độ trễ)</text>

          <!-- Clean Actor -> Use Case Associations -->
          <line x1="112" y1="168" x2="236" y2="142" stroke="#1d4ed8" stroke-width="1.5"/>
          <line x1="112" y1="184" x2="236" y2="286" stroke="#1d4ed8" stroke-width="1.5"/>
          <path d="M112,192 Q176,228 236,434" fill="none" stroke="#1d4ed8" stroke-width="1.5"/>

          <line x1="112" y1="398" x2="236" y2="156" stroke="#0f766e" stroke-width="1.4"/>
          <line x1="112" y1="412" x2="236" y2="306" stroke="#0f766e" stroke-width="1.4"/>
          <line x1="112" y1="426" x2="236" y2="450" stroke="#0f766e" stroke-width="1.4"/>

          <!-- Right Actors -> Use Cases (no crossing text!) -->
          <line x1="1032" y1="108" x2="918" y2="106" stroke="#b45309" stroke-width="1.5"/>

          <line x1="1032" y1="252" x2="918" y2="200" stroke="#1d4ed8" stroke-width="1.5"/>
          <line x1="1032" y1="266" x2="918" y2="284" stroke="#1d4ed8" stroke-width="1.5"/>
          <line x1="1032" y1="280" x2="918" y2="378" stroke="#1d4ed8" stroke-width="1.5"/>

          <line x1="1032" y1="436" x2="918" y2="474" stroke="#6d28d9" stroke-width="1.5"/>

          <line x1="1032" y1="578" x2="918" y2="578" stroke="#334155" stroke-width="1.5"/>
          <path d="M1032,566 L962,530 L962,130 L914,116" fill="none" stroke="#94a3b8" stroke-width="1.2"/>

          <!-- Valid UML «include» from UC-05 & UC-04 to UC-06 (routed neatly on left rail inside boundary) -->
          <path d="M634,106 L576,106 L576,274 L634,274" fill="none" stroke="#1d4ed8" stroke-width="1.5" stroke-dasharray="5,4" marker-end="url(#ucArr)"/>
          <path d="M634,196 L596,196 L596,292 L634,292" fill="none" stroke="#1d4ed8" stroke-width="1.5" stroke-dasharray="5,4" marker-end="url(#ucArr)"/>
          <rect x="536" y="140" width="84" height="22" rx="5" fill="#ffffff" stroke="#93c5fd"/>
          <text x="578" y="155" text-anchor="middle" font-size="11" font-weight="600" fill="#1d4ed8">«include»</text>

          <!-- Legend -->
          <rect x="206" y="664" width="736" height="44" rx="9" fill="#f8fafc" stroke="#cbd5e1"/>
          <text x="224" y="691" font-size="12" font-weight="700" fill="#334155">Chú giải UML:</text>
          <g transform="translate(338, 685)" stroke="#334155" stroke-width="1.5" fill="none">
            <circle cx="0" cy="-7" r="4"/>
            <line x1="0" y1="-3" x2="0" y2="6"/>
            <line x1="-6" y1="0" x2="6" y2="0"/>
            <line x1="0" y1="6" x2="-4" y2="12"/>
            <line x1="0" y1="6" x2="4" y2="12"/>
          </g>
          <text x="352" y="691" font-size="11.5" fill="#334155">Tác nhân</text>
          <ellipse cx="448" cy="686" rx="20" ry="10" fill="#eff6ff" stroke="#1d4ed8" stroke-width="1.5"/>
          <text x="476" y="691" font-size="11.5" fill="#334155">Ca sử dụng (UC-01..09)</text>
          <line x1="634" y1="686" x2="670" y2="686" stroke="#334155" stroke-width="1.5"/>
          <text x="678" y="691" font-size="11.5" fill="#334155">Tương tác</text>
          <line x1="756" y1="686" x2="800" y2="686" stroke="#1d4ed8" stroke-width="1.5" stroke-dasharray="4,3" marker-end="url(#ucArr)"/>
          <text x="808" y="691" font-size="11.5" fill="#334155">«include» (UML 2.5)</text>
        </svg>
      </div>
    `,
  },

  // Sơ đồ CSDL tổng quát dạng ERD liên dịch vụ
  buildErdDiagram({
    name: "hinh-2-19-csdl-tong-quat",
    title: "SƠ ĐỒ CƠ SỞ DỮ LIỆU TỔNG QUÁT VÀ LIÊN KẾT THỰC THỂ LIÊN DỊCH VỤ",
    width: 1160,
    height: 670,
    entities: [
      {
        id: "Branch DB: orders",
        x: 34,
        y: 112,
        w: 258,
        cols: [
          ["order_id", "PK"],
          ["branch_id (POS01/02/ONLINE)", ""],
          ["status / status_rank", ""],
          ["cancel_flag / close_reason", ""],
          ["items / created_at", ""],
        ],
      },
      {
        id: "Branch DB: outbox_events",
        x: 34,
        y: 314,
        w: 258,
        cols: [
          ["id / event_id", "PK, UNI"],
          ["order_id", "FK"],
          ["kind (TAO_DON/HUY)", ""],
          ["attempted / sent_at", ""],
        ],
      },
      {
        id: "Branch DB: menu_cache",
        x: 34,
        y: 480,
        w: 258,
        cols: [
          ["dish_id", "PK"],
          ["status (CON/HET/AN)", ""],
          ["epoch / seq", ""],
        ],
      },
      {
        id: "Inventory DB: inventory_orders",
        x: 438,
        y: 112,
        w: 280,
        cols: [
          ["order_id (UUID logic)", "PK"],
          ["origin_branch", ""],
          ["status (DANG_GIU/...)", ""],
          ["reason / updated_at", ""],
        ],
      },
      {
        id: "Inventory DB: stock & reservations",
        x: 438,
        y: 304,
        w: 280,
        cols: [
          ["order_id / ingredient_id", "PK, FK"],
          ["available / reserved", ""],
          ["consumed / wasted", ""],
          ["needs_check", ""],
        ],
      },
      {
        id: "Inventory DB: dish_status",
        x: 438,
        y: 480,
        w: 280,
        cols: [
          ["dish_id", "PK"],
          ["status (CON/HET/AN)", ""],
          ["epoch / seq (menu_version)", ""],
        ],
      },
      {
        id: "Central DB: orders & heartbeat",
        x: 856,
        y: 112,
        w: 270,
        cols: [
          ["order_id / branch_id", "PK"],
          ["status / close_reason", ""],
          ["beat_at (mốc dữ liệu)", ""],
        ],
      },
      {
        id: "Kitchen DB: kitchen_orders",
        x: 856,
        y: 304,
        w: 270,
        cols: [
          ["order_id (UUID logic)", "PK"],
          ["status (CHO_NAU/DANG_NAU/...)", ""],
          ["origin_branch / cancel_branches", ""],
          ["reserved / spoiled", ""],
        ],
      },
      {
        id: "Kitchen DB: flagged_ingredients",
        x: 856,
        y: 480,
        w: 270,
        cols: [
          ["ingredient_id", "PK"],
          ["needs_check", ""],
          ["epoch / seq", ""],
        ],
      },
    ],
    relations: [
      { from: "Branch DB: orders", to: "Branch DB: outbox_events", fromSide: "b", toSide: "t", label: "chờ gửi", cardFrom: "1", cardTo: "N", dw: 40 },
      { from: "Branch DB: orders", to: "Inventory DB: inventory_orders", fromSide: "r", toSide: "l", fromOff: -9.5, label: "OrderCreated", cardFrom: "1", cardTo: "0..1", dw: 52, c1y: -4, c2y: -4 },
      { from: "Branch DB: orders", to: "Central DB: orders & heartbeat", fromSide: "t", toSide: "t", route: "u", dx: 578, dy: 68, label: "WAL Replication", cardFrom: "1", cardTo: "1", dw: 62 },
      { from: "Inventory DB: inventory_orders", to: "Inventory DB: stock & reservations", fromSide: "b", toSide: "t", label: "giữ kho", cardFrom: "1", cardTo: "N", dw: 40 },
      { from: "Inventory DB: inventory_orders", to: "Kitchen DB: kitchen_orders", fromSide: "r", toSide: "l", dx: 787, dy: 256, label: "OrderReserved", cardFrom: "1", cardTo: "0..1", dw: 56 },
      { from: "Inventory DB: dish_status", to: "Branch DB: menu_cache", fromSide: "l", toSide: "r", label: "menu-events", cardFrom: "1", cardTo: "N", dw: 50 },
      { from: "Inventory DB: stock & reservations", to: "Kitchen DB: flagged_ingredients", fromSide: "r", toSide: "l", fromOff: 22, dx: 787, dy: 462, label: "cờ kiểm kho", cardFrom: "1", cardTo: "0..1", dw: 44 },
    ],
    notes: [
      {
        x: 34,
        y: 608,
        w: 1092,
        h: 38,
        text: "Các thực thể giữa 4 mô hình lược đồ CSDL (6 thực thể PostgreSQL) liên thông nghiệp vụ theo order_id (UUID) qua Kafka hoặc Logical Replication; bảng hạ tầng processed_events, alerts có trong từng dịch vụ.",
      },
    ],
  }),

  // ERD 1: Inventory DB (9 bảng)
  buildErdDiagram({
    name: "er-inventory-db",
    title: "SƠ ĐỒ THỰC THỂ – QUAN HỆ (ERD): INVENTORY DB (9 BẢNG)",
    width: 1160,
    height: 700,
    entities: [
      {
        id: "inventory_orders",
        x: 34,
        y: 56,
        w: 256,
        cols: [
          ["order_id", "PK"],
          ["origin_branch", ""],
          ["status", ""],
          ["reason", ""],
          ["order_created_at", ""],
          ["updated_at", ""],
        ],
      },
      {
        id: "inventory_reservations",
        x: 444,
        y: 56,
        w: 266,
        cols: [
          ["order_id", "PK, FK"],
          ["ingredient_id", "PK, FK"],
          ["quantity", ""],
          ["outcome", ""],
        ],
      },
      {
        id: "stock",
        x: 866,
        y: 56,
        w: 256,
        cols: [
          ["ingredient_id", "PK"],
          ["name / unit", ""],
          ["available", ""],
          ["reserved", ""],
          ["consumed / wasted", ""],
          ["needs_check", ""],
        ],
      },
      {
        id: "alerts",
        x: 34,
        y: 288,
        w: 256,
        infra: true,
        cols: [
          ["id", "PK"],
          ["kind / source_topic", "UNI*"],
          ["order_id / event_id", ""],
          ["detail / created_at", ""],
        ],
      },
      {
        id: "recipes",
        x: 444,
        y: 288,
        w: 266,
        cols: [
          ["dish_id", "PK"],
          ["ingredient_id", "PK, FK"],
          ["quantity", ""],
        ],
      },
      {
        id: "outbox_events",
        x: 866,
        y: 288,
        w: 256,
        infra: true,
        cols: [
          ["id", "PK"],
          ["event_id", "UNI"],
          ["topic / msg_key", ""],
          ["payload / sent_at", ""],
        ],
      },
      {
        id: "dish_status",
        x: 34,
        y: 486,
        w: 256,
        cols: [
          ["dish_id", "PK"],
          ["status", ""],
          ["epoch", ""],
          ["seq", ""],
        ],
      },
      {
        id: "menu_version",
        x: 444,
        y: 486,
        w: 266,
        cols: [
          ["id", "PK"],
          ["epoch", ""],
          ["seq", ""],
        ],
      },
      {
        id: "processed_events",
        x: 866,
        y: 486,
        w: 256,
        infra: true,
        cols: [
          ["event_id", "PK"],
          ["processed_at", ""],
        ],
      },
    ],
    relations: [
      { from: "inventory_orders", to: "inventory_reservations", fromSide: "r", toSide: "l", fromOff: -19, label: "giữ", cardFrom: "1", cardTo: "N", dw: 36 },
      { from: "stock", to: "inventory_reservations", fromSide: "l", toSide: "r", fromOff: -19, label: "thuộc", cardFrom: "1", cardTo: "N", dw: 38 },
      { from: "stock", to: "recipes", fromSide: "b", toSide: "r", route: "vh", dx: 792, dy: 244, label: "dùng trong", cardFrom: "1", cardTo: "N", dw: 46, c1x: -18, c2y: -10 },
      { from: "dish_status", to: "recipes", fromSide: "t", toSide: "l", fromOff: 60, route: "vh", dx: 344, dy: 428, label: "gồm", cardFrom: "1", cardTo: "N", dw: 32, c1x: 12, c2y: -6 },
      { from: "menu_version", to: "dish_status", fromSide: "l", toSide: "r", fromOff: 9.5, toOff: 0, label: "cấp version", cardFrom: "1", cardTo: "N", dw: 48, c1y: -4, c2y: -4 },
      { from: "inventory_orders", to: "alerts", fromSide: "b", toSide: "t", label: "cảnh báo", cardFrom: "0..1", cardTo: "N", dw: 42, c1x: 8, c2x: 8 },
    ],
    notes: [
      {
        x: 34,
        y: 636,
        w: 1088,
        h: 36,
        text: "Toàn bộ mối quan hệ nghiệp vụ và khóa ngoại trong Inventory DB; outbox_events, processed_events là bảng hạ tầng; UNI* chỉ khóa tổ hợp 4 cột của alerts.",
      },
    ],
  }),

  // ERD 2: Kitchen DB (5 bảng)
  buildErdDiagram({
    name: "er-kitchen-db",
    title: "SƠ ĐỒ THỰC THỂ – QUAN HỆ (ERD): KITCHEN DB (5 BẢNG)",
    width: 1120,
    height: 520,
    entities: [
      {
        id: "kitchen_orders",
        x: 44,
        y: 58,
        w: 280,
        cols: [
          ["order_id", "PK"],
          ["status", ""],
          ["origin_branch", ""],
          ["cancel_branches", ""],
          ["cancel_reasons", ""],
          ["cancelled_by / close_reason", ""],
          ["items / reserved / spoiled", ""],
          ["order_created_at / updated_at", ""],
        ],
      },
      {
        id: "flagged_ingredients",
        x: 486,
        y: 58,
        w: 250,
        cols: [
          ["ingredient_id", "PK"],
          ["needs_check", ""],
          ["epoch", ""],
          ["seq", ""],
        ],
      },
      {
        id: "processed_events",
        x: 840,
        y: 58,
        w: 244,
        infra: true,
        cols: [
          ["event_id", "PK"],
          ["processed_at", ""],
        ],
      },
      {
        id: "alerts",
        x: 44,
        y: 320,
        w: 280,
        infra: true,
        cols: [
          ["id", "PK"],
          ["kind / source_topic", "UNI*"],
          ["order_id / event_id", ""],
          ["detail / created_at", ""],
        ],
      },
      {
        id: "outbox_events",
        x: 486,
        y: 300,
        w: 250,
        infra: true,
        cols: [
          ["id", "PK"],
          ["event_id", "UNI"],
          ["topic / msg_key", ""],
          ["payload / sent_at", ""],
        ],
      },
    ],
    relations: [
      { from: "kitchen_orders", to: "flagged_ingredients", fromSide: "r", toSide: "l", fromOff: -38, label: "đối chiếu", cardFrom: "N", cardTo: "M", dw: 44 },
      { from: "kitchen_orders", to: "alerts", fromSide: "b", toSide: "t", label: "cảnh báo", cardFrom: "0..1", cardTo: "N", dw: 42, c1x: 8, c2x: 8 },
    ],
    notes: [
      {
        x: 44,
        y: 458,
        w: 1040,
        h: 36,
        text: "kitchen_orders lưu tập trung thông tin giữ nguyên liệu (reserved JSONB) để đối chiếu cảnh báo trực tiếp với flagged_ingredients; outbox_events, processed_events là bảng hạ tầng.",
      },
    ],
  }),

  // ERD 3: Branch DB (8 bảng)
  buildErdDiagram({
    name: "er-branch-db",
    title: "SƠ ĐỒ THỰC THỂ – QUAN HỆ (ERD): BRANCH DB — POS01, POS02, ONLINE (8 BẢNG)",
    width: 1160,
    height: 670,
    entities: [
      {
        id: "orders",
        x: 34,
        y: 56,
        w: 268,
        cols: [
          ["order_id", "PK"],
          ["branch_id", ""],
          ["status / status_rank", ""],
          ["close_reason", ""],
          ["cancel_flag", ""],
          ["cancel_requested_at", ""],
          ["cancel_message", ""],
          ["items / created_at", ""],
        ],
      },
      {
        id: "outbox_events",
        x: 454,
        y: 56,
        w: 268,
        cols: [
          ["id", "PK"],
          ["event_id", "UNI"],
          ["order_id", "FK"],
          ["kind (TAO_DON/HUY)", ""],
          ["topic / payload", ""],
          ["attempted / sent_at", ""],
        ],
      },
      {
        id: "dishes",
        x: 874,
        y: 56,
        w: 248,
        cols: [
          ["dish_id", "PK"],
          ["name", ""],
        ],
      },
      {
        id: "menu_cache",
        x: 874,
        y: 256,
        w: 248,
        cols: [
          ["dish_id", "PK"],
          ["status", ""],
          ["epoch", ""],
          ["seq", ""],
        ],
      },
      {
        id: "menu_cache_meta",
        x: 454,
        y: 256,
        w: 268,
        cols: [
          ["id", "PK"],
          ["epoch", ""],
          ["last_heard_at", ""],
          ["newest_epoch", ""],
        ],
      },
      {
        id: "replication_heartbeat",
        x: 34,
        y: 344,
        w: 268,
        cols: [
          ["branch_id", "PK"],
          ["beat_at", ""],
        ],
      },
      {
        id: "alerts",
        x: 454,
        y: 458,
        w: 268,
        infra: true,
        cols: [
          ["id", "PK"],
          ["kind / source_topic", "UNI*"],
          ["order_id / event_id", ""],
          ["detail / created_at", ""],
        ],
      },
      {
        id: "processed_events",
        x: 874,
        y: 458,
        w: 248,
        infra: true,
        cols: [
          ["event_id", "PK"],
          ["processed_at", ""],
        ],
      },
    ],
    relations: [
      { from: "orders", to: "outbox_events", fromSide: "r", toSide: "l", fromOff: -19, label: "chờ gửi", cardFrom: "1", cardTo: "N", dw: 38 },
      { from: "dishes", to: "menu_cache", fromSide: "b", toSide: "t", label: "lưu đệm", cardFrom: "1", cardTo: "0..1", dw: 40 },
      { from: "menu_cache_meta", to: "menu_cache", fromSide: "r", toSide: "l", label: "độ mới", cardFrom: "1", cardTo: "N", dw: 40 },
      { from: "replication_heartbeat", to: "orders", fromSide: "t", toSide: "b", label: "đồng bộ", cardFrom: "1", cardTo: "N", dw: 42 },
      { from: "orders", to: "alerts", fromSide: "r", toSide: "l", fromOff: 56, route: "hv", dx: 378, dy: 514, label: "cảnh báo", cardFrom: "0..1", cardTo: "N", dw: 42 },
    ],
    notes: [
      {
        x: 34,
        y: 604,
        w: 1088,
        h: 36,
        text: "Hai bảng orders và replication_heartbeat bật logical publication sang Central Order Replica; bảng menu_cache cập nhật đơn điệu theo phiên bản (epoch, seq).",
      },
    ],
  }),

  // ERD 4: Central Order Replica (2 bảng)
  buildErdDiagram({
    name: "er-central-db",
    title: "SƠ ĐỒ THỰC THỂ – QUAN HỆ (ERD): CENTRAL ORDER REPLICA (2 BẢNG)",
    width: 960,
    height: 350,
    entities: [
      {
        id: "replication_heartbeat",
        x: 56,
        y: 96,
        w: 268,
        cols: [
          ["branch_id", "PK"],
          ["beat_at", ""],
        ],
      },
      {
        id: "orders",
        x: 590,
        y: 58,
        w: 300,
        cols: [
          ["order_id", "PK"],
          ["branch_id", ""],
          ["status / status_rank", ""],
          ["close_reason", ""],
          ["cancel_flag", ""],
          ["cancel_requested_at", ""],
          ["cancel_message", ""],
          ["items / created_at", ""],
        ],
      },
    ],
    relations: [
      { from: "replication_heartbeat", to: "orders", fromSide: "r", toSide: "l", toOff: -19, label: "mốc dữ liệu", cardFrom: "1", cardTo: "N", dw: 50 },
    ],
    notes: [
      {
        x: 56,
        y: 288,
        w: 834,
        h: 36,
        text: "Central Order Replica nhận dữ liệu nhân bản bất đồng bộ từ ba nguồn POS01, POS02 và ONLINE phục vụ truy vấn báo cáo nhất quán.",
      },
    ],
  }),
];
