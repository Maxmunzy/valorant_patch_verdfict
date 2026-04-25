import type { Metadata } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://whosnxt.app";

const EN_DESCRIPTION =
  "ML predictions for which Valorant agents get nerfed or buffed next patch. Walk-forward validated.";

/**
 * /en/* 모든 페이지에 공통으로 적용되는 영문 메타데이터.
 * root layout(KO) 의 og:description 이 영문 페이지에 새는 걸 방지하기 위해 nested layout 으로 override.
 */
export const metadata: Metadata = {
  title: {
    default: "WHO'S NEXT? // Valorant Patch Predictor",
    template: "%s",
  },
  description: EN_DESCRIPTION,
  openGraph: {
    type: "website",
    siteName: "WHOSNXT // PATCH VERDICT",
    title: "WHO'S NEXT? // Valorant Patch Predictor",
    description: EN_DESCRIPTION,
    url: `${SITE_URL}/en`,
  },
  twitter: {
    card: "summary_large_image",
    title: "WHO'S NEXT? // Valorant Patch Predictor",
    description: EN_DESCRIPTION,
  },
};

export default function EnLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
