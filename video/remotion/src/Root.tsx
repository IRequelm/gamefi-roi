import "./index.css";
import { MyComposition } from "./Composition";
import { AcurastBridge } from "./AcurastBridge";

export const RemotionRoot: React.FC = () => {
  return <>
    <MyComposition />
    <AcurastBridge />
  </>;
};
