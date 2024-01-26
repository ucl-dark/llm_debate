interface SliderProps {
  value: number;
  onChange: (value: number) => void;
  label?: string;
  min?: number;
  max?: number;
  step?: number;
}
const Slider = ({
  value,
  onChange,
  label,
  min = 0,
  max = 100,
  step = 1,
}: SliderProps) => {
  return (
    <div className="flex flex-col flex-grow w-full">
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {label}
        </label>
      )}
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="slider w-full "
      />
    </div>
  );
};

export default Slider;
