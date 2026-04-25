import CategoryContent from "@/components/CategoryContent";

export const revalidate = 300;

export default async function CategoryPageEn({
  params,
}: {
  params: Promise<{ type: string }>;
}) {
  const { type } = await params;
  return <CategoryContent type={type} locale="en" />;
}
