import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface PrintablePageLayoutProps {
  pageNumber: number;
  totalPages: number;
  characterName: string;
  characterSubhead: string;
  pageTitle: string;
  children: ReactNode;
  className?: string;
  isFirstPage?: boolean;
}

export function PrintablePageLayout({
  pageNumber,
  totalPages,
  characterName,
  characterSubhead,
  pageTitle,
  children,
  className,
  isFirstPage = false,
}: PrintablePageLayoutProps) {
  return (
    <div
      className={cn(
        "printable-page relative flex flex-col justify-between bg-white text-slate-900 border border-slate-300 shadow-md mx-auto my-4 print:my-0 print:border-none print:shadow-none print:bg-white box-border",
        // US Letter standard dimensions in 96dpi screen preview: 8.5in x 11in = 816px x 1056px
        "w-full max-w-[8.5in] min-h-[11in] p-6 print:p-0 print:w-full print:max-w-none print:min-h-0",
        "print:break-after-page print:page-break-after-always",
        className,
      )}
      style={{
        pageBreakAfter: pageNumber < totalPages ? "always" : "auto",
        breakAfter: pageNumber < totalPages ? "page" : "auto",
      }}
    >
      <div className="flex-1 flex flex-col">
        {/* Sub-header for subsequent pages (Page 2+) */}
        {!isFirstPage && (
          <header className="mb-4 pb-2 border-b-2 border-slate-800 flex items-center justify-between text-xs">
            <div>
              <span className="font-display font-bold text-base text-slate-900 uppercase tracking-wide">
                {characterName}
              </span>
              <span className="text-slate-600 ml-2 font-medium">
                — {characterSubhead}
              </span>
            </div>
            <div className="font-display font-semibold text-slate-700 uppercase tracking-widest text-xs">
              {pageTitle}
            </div>
          </header>
        )}

        {/* Page Main Content */}
        <div className="flex-1 flex flex-col">{children}</div>
      </div>

      {/* Page Footer */}
      <footer className="mt-4 pt-2 border-t border-slate-300 flex items-center justify-between text-[10px] text-slate-500 uppercase tracking-wider font-medium">
        <div>D&D 2024 Character Record</div>
        <div className="font-semibold text-slate-700">
          {characterName} • Page {pageNumber} of {totalPages}
        </div>
        <div>{pageTitle}</div>
      </footer>
    </div>
  );
}
