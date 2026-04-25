import { PageContainer } from "../layout/PageContainer";
import { ChainExplorer } from "../components/ChainExplorer";

export function Chain() {
  return (
    <PageContainer title="Chain" subtitle="Anchored provenance records">
      <ChainExplorer />
    </PageContainer>
  );
}
