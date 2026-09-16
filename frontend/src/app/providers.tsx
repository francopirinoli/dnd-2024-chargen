import { useEffect } from "react";
import { QueryClientProvider, useQuery } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { queryClient } from "@/lib/queryClient";
import { router } from "./router";
import { api } from "@/lib/api";
import { useSupplementStore } from "@/store/supplementStore";
import { UpdatePrompt } from "@/components/UpdatePrompt";
import { OfflineIndicator } from "@/components/OfflineIndicator";

function SupplementSync() {
  const { data: supplements } = useQuery({
    queryKey: ["supplements"],
    queryFn: () => api.supplements.list(),
  });

  useEffect(() => {
    if (supplements && supplements.length > 0) {
      useSupplementStore.getState().setSupplements(supplements);
    }
  }, [supplements]);

  return null;
}

export function Providers() {
  return (
    <QueryClientProvider client={queryClient}>
      <SupplementSync />
      <RouterProvider router={router} />
      <UpdatePrompt />
      <OfflineIndicator />
    </QueryClientProvider>
  );
}
