import { useEffect, useRef } from "react";
import * as echarts from "echarts/core";
import { LineChart, BarChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  AriaComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { EChartsCoreOption } from "echarts/core";
echarts.use([
  LineChart,
  BarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  AriaComponent,
  CanvasRenderer,
]);
export function Chart({
  option,
  label,
  height = 260,
}: {
  option: EChartsCoreOption;
  label: string;
  height?: number;
}) {
  const element = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const chart = echarts.init(element.current!);
    chart.setOption({
      ...option,
      aria: { enabled: true, label: { description: label } },
      animation: false,
    });
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(element.current!);
    return () => {
      observer.disconnect();
      chart.dispose();
    };
  }, [option, label]);
  return (
    <div
      ref={element}
      role="img"
      aria-label={label}
      style={{ height, width: "100%" }}
    />
  );
}
export const chartTheme = {
  textStyle: { fontFamily: "system-ui", color: "#94a3b8" },
  grid: { left: 48, right: 18, top: 25, bottom: 36 },
  tooltip: {
    trigger: "axis",
    backgroundColor: "#19232f",
    borderColor: "#344253",
    textStyle: { color: "#f1f5f9" },
  },
  xAxis: {
    type: "category",
    axisLine: { lineStyle: { color: "#2a3440" } },
    axisTick: { show: false },
    axisLabel: { color: "#94a3b8", fontSize: 12 },
  },
  yAxis: {
    type: "value",
    splitLine: { lineStyle: { color: "#202a36", type: "dashed" } },
    axisLabel: { color: "#94a3b8", fontSize: 12 },
  },
};
